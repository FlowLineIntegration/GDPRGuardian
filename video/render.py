#!/usr/bin/env python3
"""Render the Gardien RGPD / GDPR Guardian launch video from video/scene.html, frame by frame.

    python video/render.py                       # everything: fr and en, full video and social cut
    python video/render.py --lang fr --format wide    # one language, one format
    python video/render.py --lang fr --check     # timeline, reading check and transcript only, no video
    python video/render.py --lang en --format social --frame 4 20   # PNGs at 4 s and 20 s, for a quick look

Two formats: wide (1920 x 1080, the full video) and social (1080 x 1350, a shorter cut with larger type for phone
feeds). Reads video/facts.<lang>.json (all text and figures) and site/data/quality.json (test counts, red-team and
real-corpus counts and the confidence index, shown as "being measured" while it is "—"): re-run the same command once
quality.json changes and the video follows. The poster is written as a palette PNG (lighten_poster), since the site
loads it with the page.

Writes into video/out/: <stem>.mp4 (30 fps, H.264 High yuv420p BT.709, CRF 17, faststart, no audio),
<stem>-poster.png, <stem>-transcript.txt (every on-screen text, in order), and review/ (timeline and reading check,
contact sheets with one frame every 2 seconds). The social cut's stem ends in -social.

How: the page is loaded in headless Chromium (Playwright) from a private origin served from the repository (no
network); window.render(t) draws the frame at t seconds without any clock, so frames are captured in parallel
chunks, piped into ffmpeg, then joined without re-encoding. Identical consecutive frames are captured once.

Needs: pip install -r video/requirements.txt, then python -m playwright install chromium.
ffmpeg: $GR_FFMPEG, else imageio-ffmpeg's static binary, else ffmpeg on the PATH.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

VIDEO = Path(__file__).resolve().parent
ROOT = VIDEO.parent
OUT = VIDEO / "out"
ORIGIN = "http://video.local"
SERVED = (VIDEO, ROOT / "site" / "static" / "fonts", ROOT / "site" / "data")
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".woff2": "font/woff2",
}
SIZES = {"wide": (1920, 1080), "social": (1080, 1350)}
LANGS = ("fr", "en")
FORMATS = ("wide", "social")


def log(msg: str) -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------- tools

def find_ffmpeg() -> str:
    env = os.environ.get("GR_FFMPEG")
    if env:
        return env
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 - any failure falls back to the PATH
        pass
    exe = shutil.which("ffmpeg")
    if not exe:
        raise SystemExit("ffmpeg not found: pip install imageio-ffmpeg, or set GR_FFMPEG")
    return exe


def x264_args(fps: int, crf: int = 17) -> list[str]:
    # BT.709, limited range, explicit tags; no B-frames so that the parallel segments join cleanly without re-encoding.
    return [
        "-vf", "scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p,"
               "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv",
        "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-tune", "animation", "-bf", "0",
        "-profile:v", "high", "-level:v", "4.1", "-g", str(fps * 2), "-r", str(fps),
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
        "-an",
    ]


def run(cmd: list[str]) -> str:
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise RuntimeError(f"{Path(cmd[0]).name} failed ({res.returncode}): {res.stderr[-2000:]}")
    return res.stdout + res.stderr


# ---------------------------------------------------------------- the page

def make_handler(quality: Path | None):
    def handle(route):
        url = urllib.parse.urlsplit(route.request.url)
        if f"{url.scheme}://{url.netloc}" != ORIGIN:
            route.abort()  # nothing leaves the machine
            return
        rel = urllib.parse.unquote(url.path).lstrip("/")
        path = (ROOT / rel).resolve()
        if quality is not None and rel == "site/data/quality.json":
            path = quality
        elif not path.is_file() or not any(path.is_relative_to(d) for d in SERVED):
            route.fulfill(status=404, body="not found")
            return
        route.fulfill(status=200, body=path.read_bytes(),
                      headers={"content-type": TYPES.get(path.suffix, "application/octet-stream"),
                               "cache-control": "no-store"})
    return handle


def open_page(pw, lang: str, quality: Path | None, fmt: str = "wide"):
    width, height = SIZES[fmt]
    browser = pw.chromium.launch(args=["--force-color-profile=srgb", "--font-render-hinting=none",
                                       "--disable-lcd-text", "--hide-scrollbars"])
    context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1,
                                  color_scheme="light")
    context.route("**/*", make_handler(quality))
    page = context.new_page()
    page.goto(f"{ORIGIN}/video/scene.html?lang={lang}&fmt={fmt}&capture=1")
    page.wait_for_function("window.READY === true || !!window.BOOT_ERROR", timeout=60_000)
    err = page.evaluate("window.BOOT_ERROR || null")
    if err:
        raise SystemExit(f"scene.html failed to load: {err}")
    if not page.evaluate("window.FONTS_OK"):
        raise SystemExit("GR Sans / GR Mono did not load from site/static/fonts")
    return browser, page


def render_chunk(job: tuple) -> tuple[int, int, int, float]:
    lang, fmt, first, last, seg, ffmpeg, quality, fps, crf = job
    from playwright.sync_api import sync_playwright

    started = time.perf_counter()
    with sync_playwright() as pw:
        browser, page = open_page(pw, lang, Path(quality) if quality else None, fmt)
        cdp = page.context.new_cdp_session(page)
        enc = subprocess.Popen(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(fps),
             "-c:v", "png", "-i", "-", *x264_args(fps, crf), str(seg)],
            stdin=subprocess.PIPE)
        sig_prev, png, shots = None, b"", 0
        try:
            for i in range(first, last):
                sig = page.evaluate("t => window.render(t)", i / fps)
                if sig != sig_prev:
                    shot = cdp.send("Page.captureScreenshot", {"format": "png", "optimizeForSpeed": True})
                    png, sig_prev, shots = base64.b64decode(shot["data"]), sig, shots + 1
                enc.stdin.write(png)
        finally:
            enc.stdin.close()
            code = enc.wait()
            browser.close()
        if code != 0:
            raise RuntimeError(f"ffmpeg failed on frames {first}-{last}")
    return first, last, shots, time.perf_counter() - started


# ---------------------------------------------------------------- reports

def load_facts(lang: str) -> dict:
    return json.loads((VIDEO / f"facts.{lang}.json").read_text(encoding="utf-8"))


QUALITY_KEYS = ("tests_windows", "tests_linux", "redteam_operators", "real_corpora", "real_docs",
                "confidence_index", "confidence_ci_low", "confidence_ci_high", "mention_recall_pct",
                "protocol_docs", "protocol_date")


def stem_of(facts: dict, fmt: str) -> str:
    return facts["file_stem"] + ("-social" if fmt == "social" else "")


def write_reports(lang: str, fmt: str, facts: dict, info: dict) -> tuple[Path, Path]:
    stem, (width, height) = stem_of(facts, fmt), SIZES[fmt]
    tr = OUT / f"{stem}-transcript.txt"
    lines = [facts["transcript_title"], facts["transcript_note"],
             f"{info['timeline']['duration']:.1f} s · {width} x {height} · 30 fps", ""]
    lines += [f"[{row['time']}] {row['text']}" for row in info["transcript"]]
    # Fins de ligne LF partout : l'empreinte citée par le site (?v=) doit être celle du fichier du dépôt.
    # LF everywhere: the digest the site cites (?v=) must be the repository file's.
    tr.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    rd = info["readability"]
    rep = OUT / "review" / f"timeline-{lang}{'-social' if fmt == 'social' else ''}.txt"
    rep.parent.mkdir(parents=True, exist_ok=True)
    out = [f"{stem}: {rd['total']:.2f} s, {width} x {height}",
           f"reading rule: {rd['rule']['read_s_per_word']} s per word (short labels x{rd['rule']['label_weight']}),"
           f" at least {rd['rule']['min_line_s']} s per text; scenes cross-fade over {rd['rule']['crossfade_s']} s", "",
           f"{'scene':<12} {'chapter':<9} {'start':>7} {'length':>7} {'words':>6} {'slack':>6}"]
    for s in rd["scenes"]:
        out.append(f"{s['id']:<12} {str(s['chapter'] or '-'):<9} {s['start']:>7.2f} {s['dur']:>7.2f} "
                   f"{s['words']:>6} {s['slack']:>6.2f}")
    out += ["", "problems:" if rd["problems"] else "problems: none"] + [f"  {p}" for p in rd["problems"]]
    q = info["quality"]
    out += ["", "read from site/data/quality.json: " + ", ".join(f"{k}={q.get(k)!r}" for k in QUALITY_KEYS)]
    rep.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    return tr, rep


def inspect(lang: str, fmt: str, quality: Path | None, poster: Path | None = None,
            frames: list[tuple[float, Path]] | None = None) -> dict:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser, page = open_page(pw, lang, quality, fmt)
        info = {
            "timeline": page.evaluate("window.TIMELINE"),
            "transcript": page.evaluate("window.transcript()"),
            "readability": page.evaluate("window.readability()"),
            "quality": page.evaluate("fetch('../site/data/quality.json').then(r => r.json())"),
        }
        if poster:
            page.evaluate("t => window.render(t)", page.evaluate("window.posterTime()"))
            page.screenshot(path=str(poster), type="png")
            lighten_poster(poster)
        for t, png in frames or ():
            page.evaluate("t => window.render(t)", t)
            page.screenshot(path=str(png), type="png")
        browser.close()
    return info


POSTER_MAX_BYTES = 30_000  # the site loads the poster with the page


def lighten_poster(png: Path) -> int:
    """Rewrite the poster as a palette PNG (median cut, no dithering): white paper, ink, greys and the orange of the
    tags need few colours, and text stays sharp. 32 colours first, fewer only if the file is still too heavy.
    Measured on 26 October 2026: 85 to 92 KB down to 20 to 30 KB, mean error under 0.1 level out of 255."""
    from PIL import Image

    rgb = Image.open(png).convert("RGB")
    for colors in (32, 24, 16):
        rgb.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(png, optimize=True)
        if png.stat().st_size <= POSTER_MAX_BYTES:
            break
    return png.stat().st_size


def probe(ffmpeg: str, mp4: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        js = json.loads(run([ffprobe, "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                             "stream=codec_name,profile,width,height,pix_fmt,r_frame_rate,nb_read_frames,color_space"
                             ":format=duration,size", "-of", "json", str(mp4)]))
        st = js["streams"][0]
        return {"duration": float(js["format"]["duration"]), "size": int(js["format"]["size"]),
                "codec": st.get("codec_name"), "profile": st.get("profile"), "width": st["width"],
                "height": st["height"], "pix_fmt": st.get("pix_fmt"), "fps": st.get("r_frame_rate"),
                "frames": int(st.get("nb_read_frames") or 0), "color": st.get("color_space"), "via": "ffprobe"}
    text = run([ffmpeg, "-hide_banner", "-i", str(mp4), "-map", "0:v", "-c", "copy", "-f", "null", "-"])
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", text)
    frames = re.findall(r"frame=\s*(\d+)", text)
    vid = re.search(r"Video: (\w+).*?, (\w+)\(.*?(\d{3,4})x(\d{3,4}).*?([\d.]+) fps", text)
    return {"duration": int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3]) if dur else None,
            "size": mp4.stat().st_size, "codec": vid[1] if vid else None, "pix_fmt": vid[2] if vid else None,
            "width": int(vid[3]) if vid else None, "height": int(vid[4]) if vid else None,
            "fps": vid[5] if vid else None, "frames": int(frames[-1]) if frames else None, "via": "ffmpeg"}


def contact_sheets(ffmpeg: str, mp4: Path, lang: str, fmt: str, tmp: Path, fps: int, every: float = 2.0) -> list[Path]:
    from PIL import Image, ImageDraw, ImageFont

    social = fmt == "social"
    shots = tmp / f"sheet-{lang}-{fmt}"
    shots.mkdir(parents=True, exist_ok=True)
    cols, rows, cw, ch, lab = (6, 3, 288, 360, 32) if social else (4, 4, 480, 270, 32)
    step = max(1, round(every * fps))  # exact frames 0, 60, 120… so that each label is the frame's true time
    run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(mp4), "-vf",
         f"select='not(mod(n\\,{step}))',scale={cw}:{ch}:flags=lanczos", "-fps_mode", "vfr", str(shots / "f%04d.png")])
    files = sorted(shots.glob("f*.png"))
    try:
        font = ImageFont.load_default(size=22)
    except TypeError:
        font = ImageFont.load_default()
    sheets = []
    for s in range(0, len(files), cols * rows):
        sheet = Image.new("RGB", (cols * cw + (cols + 1) * 8, rows * (ch + lab) + (rows + 1) * 8), (190, 194, 200))
        draw = ImageDraw.Draw(sheet)
        for k, f in enumerate(files[s:s + cols * rows]):
            x, y = 8 + (k % cols) * (cw + 8), 8 + (k // cols) * (ch + lab + 8)
            sheet.paste(Image.open(f).convert("RGB"), (x, y + lab))
            t = (s + k) * every
            draw.rectangle([x, y, x + cw, y + lab - 1], fill=(14, 17, 22))
            draw.text((x + 8, y + 4), f"{lang}  {int(t) // 60:02d}:{int(t) % 60:02d}", fill=(255, 255, 255), font=font)
        out = OUT / "review" / f"contact-{lang}{'-social' if social else ''}-{s // (cols * rows) + 1}.png"
        sheet.save(out, optimize=True)
        sheets.append(out)
    return sheets


# ---------------------------------------------------------------- main

def render_one(lang: str, fmt: str, args, ffmpeg: str, tmp_root: Path) -> None:
    facts = load_facts(lang)
    stem, tag = stem_of(facts, fmt), f"{lang}/{fmt}"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "review").mkdir(parents=True, exist_ok=True)
    quality = Path(args.quality).resolve() if args.quality else None

    if args.frame:
        shots = [(t, OUT / "review" / f"frame-{lang}{'-social' if fmt == 'social' else ''}-{t:06.2f}.png")
                 for t in args.frame]
        inspect(lang, fmt, quality, frames=shots)
        for t, png in shots:
            log(f"[{tag}] frame {t} s -> {png}")
        return

    t0 = time.perf_counter()
    poster = None if args.check else OUT / f"{stem}-poster.png"
    info = inspect(lang, fmt, quality, poster=poster)
    tr, rep = write_reports(lang, fmt, facts, info)
    rd = info["readability"]
    log(f"[{tag}] timeline {rd['total']:.2f} s, {len(rd['scenes'])} scenes, reading problems: {len(rd['problems'])}")
    for p in rd["problems"]:
        log(f"  ! {p}")
    log(f"[{tag}] transcript -> {tr}\n[{tag}] timeline   -> {rep}")
    if args.check:
        return
    log(f"[{tag}] poster     -> {poster} ({poster.stat().st_size} bytes, palette PNG)")

    fps = int(info["timeline"]["fps"])
    total = round(info["timeline"]["duration"] * fps)
    tmp = Path(tempfile.mkdtemp(prefix=f"gr-video-{lang}-{fmt}-", dir=tmp_root))
    n_chunks = max(1, min(total // 60, args.workers * 2))
    bounds = [round(total * k / n_chunks) for k in range(n_chunks + 1)]
    jobs = [(lang, fmt, bounds[k], bounds[k + 1], str(tmp / f"seg{k:03d}.mp4"), ffmpeg,
             str(quality) if quality else None, fps, args.crf) for k in range(n_chunks)]
    log(f"[{tag}] {total} frames in {n_chunks} chunks on {args.workers} workers…")
    shots = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for first, last, n, secs in pool.map(render_chunk, jobs):
            shots += n
            log(f"[{tag}]   frames {first:>5}-{last:<5} {n:>4} captures, {secs:5.1f} s")
    lst = tmp / "segments.txt"
    lst.write_text("".join(f"file '{Path(j[4]).as_posix()}'\n" for j in jobs), encoding="utf-8")
    mp4 = OUT / f"{stem}.mp4"
    run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", "-movflags", "+faststart", str(mp4)])
    p = probe(ffmpeg, mp4)
    log(f"[{tag}] video      -> {mp4}")
    log(f"[{tag}]   {p['width']}x{p['height']} {p['codec']} {p.get('pix_fmt')} {p['fps']} fps, {p['duration']:.2f} s, "
        f"{p['frames']} frames, {p['size'] / 1e6:.2f} MB ({shots} unique captures)")
    if p["frames"] and p["frames"] != total:
        log(f"[{tag}]   ! expected {total} frames")
    if not args.no_sheets:
        for s in contact_sheets(ffmpeg, mp4, lang, fmt, tmp, fps):
            log(f"[{tag}] contact    -> {s}")
    shutil.rmtree(tmp, ignore_errors=True)
    log(f"[{tag}] done in {time.perf_counter() - t0:.1f} s")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--lang", choices=(*LANGS, "all"), default="all")
    ap.add_argument("--format", choices=(*FORMATS, "all"), default="all",
                    help="wide (1920 x 1080, full video), social (1080 x 1350, short cut) or all")
    # 3 navigateurs au plus par défaut : chacun prend 300 à 400 Mo / at most 3 browsers by default (300-400 MB each).
    ap.add_argument("--workers", type=int, default=max(1, min(3, (os.cpu_count() or 2) // 2)))
    ap.add_argument("--crf", type=int, default=17, help="x264 quality (default 17, visually lossless; lower is larger)")
    ap.add_argument("--quality", help="another quality.json to render with (default: site/data/quality.json)")
    ap.add_argument("--tmp", help="folder for temporary segments (default: the system temporary folder)")
    ap.add_argument("--check", action="store_true", help="timeline, reading check and transcript only")
    ap.add_argument("--frame", type=float, nargs="+", help="render frames at these times (seconds) to out/review/")
    ap.add_argument("--no-sheets", action="store_true", help="skip the contact sheets")
    args = ap.parse_args()
    tmp_root = Path(args.tmp) if args.tmp else Path(tempfile.gettempdir())
    tmp_root.mkdir(parents=True, exist_ok=True)
    ffmpeg = "" if (args.check or args.frame) else find_ffmpeg()
    for lang in (LANGS if args.lang == "all" else (args.lang,)):
        for fmt in (FORMATS if args.format == "all" else (args.format,)):
            render_one(lang, fmt, args, ffmpeg, tmp_root)


if __name__ == "__main__":
    main()
