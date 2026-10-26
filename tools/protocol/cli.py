"""Ligne de commande du protocole public / public protocol command line.

    python -m tools.protocol plan [--count]                 plan pré-enregistré (et décompte exact, sans service)
    python -m tools.protocol registration [--bundle F.pyz]  empreintes à publier AVANT le lancement
    python -m tools.protocol pack-real --cache DIR --out F [--split dev]
                                                            paquet des corpus réels (hors dépôt, pour la mémoire
                                                            vive) ; --split dev pour tout essai (moitié test intacte)
    python -m tools.protocol bundle --out F.pyz             paquet autonome pour le serveur (stdlib + Faker)
    python -m tools.protocol run --socket S --token-stdin --engine-id IMAGE --real /real/pack.jsonl.gz --work DIR
    python -m tools.protocol status --work DIR              avancement (compteurs seulement)
    python -m tools.protocol verify-engine --work DIR --engine-id IMAGE
    python -m tools.protocol report --work DIR [--disclose CODE[:DÉTAIL]]
                                                            résultats JSON + Markdown (campagne terminée)
    python -m tools.protocol merge-quality RESULTS.json site/data/quality.json
    python -m tools.protocol crosscheck --socket S ...      contrôle croisé : service contre évaluation en processus
    python -m tools.protocol crosscheck-summary --runs auto=A.json FR=B.json --out-dir D --date J --engine-note N
                                                            résumé publié du contrôle croisé (JSON + Markdown)

Codes de sortie de `run` : 0 terminée, 3 service injoignable (reprendre), 4 en pause (reprendre), 5 refus.
Exit codes of `run`: 0 complete, 3 service unreachable (resume), 4 paused (resume), 5 refused.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path
from typing import Any

from tools.protocol import spec

LABELS_FILE = Path(__file__).with_name("labels.json")


def load_label_keys() -> dict[str, str]:
    """Texte affiché d'une balise -> libellé du moteur (fichier figé, vérifié par les tests) / display -> label."""
    try:
        return json.loads(LABELS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        import importlib.resources as resources

        return json.loads(resources.files("tools.protocol").joinpath("labels.json").read_text(encoding="utf-8"))


def label_table() -> dict[str, str]:
    """Table « texte affiché -> libellé » tirée du moteur (pack FR et libellés communs) / table from the engine.

    Un texte affiché par deux libellés (packs étrangers) n'y entre pas : ambigu / ambiguous displays are left out.
    """
    from gdprguardian import Anonymizer
    from gdprguardian.labels import LABELS

    Anonymizer(countries=("FR",))
    seen: dict[str, set[str]] = {}
    for language in ("fr", "en"):
        for key in sorted(LABELS._labels):
            seen.setdefault(LABELS.display(key, language, False), set()).add(key)
    return {display: next(iter(keys)) for display, keys in sorted(seen.items()) if len(keys) == 1}


def cmd_labels(_args: argparse.Namespace) -> int:
    table = label_table()
    LABELS_FILE.write_text(json.dumps(table, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(table)} textes affichés / displays -> {LABELS_FILE}")
    return 0


def _int_list(raw: str) -> tuple[int, ...]:
    return tuple(int(x) for x in raw.split(",") if x.strip())


def _plan_args(parser: argparse.ArgumentParser) -> None:
    """Réglages d'un plan réduit (essais seulement : un plan non standard n'est jamais publié) / scaled plan."""
    group = parser.add_argument_group("plan réduit, essais seulement / scaled plan, tests only")
    group.add_argument("--synthetic-seeds", type=_int_list, default=spec.SYNTHETIC_SEEDS)
    group.add_argument("--synthetic-docs", type=int, default=spec.SYNTHETIC_DOCS_PER_SEED, help="par graine / per seed")
    group.add_argument("--redteam-seeds", type=_int_list, default=spec.REDTEAM_SEEDS)
    group.add_argument("--redteam-bases", type=int, default=spec.REDTEAM_BASES_PER_SEED, help="par graine / per seed")
    group.add_argument("--unit-synthetic", type=int, default=spec.UNIT_SYNTHETIC_DOCS)
    group.add_argument("--unit-redteam", type=int, default=spec.UNIT_REDTEAM_BASES)
    group.add_argument("--unit-real", type=int, default=spec.UNIT_REAL_DOCS)


def _build_plan(args: argparse.Namespace, real_counts: dict[str, int]) -> Any:
    from tools.protocol.plan import build_plan

    return build_plan(synthetic_seeds=args.synthetic_seeds, synthetic_docs_per_seed=args.synthetic_docs,
                      redteam_seeds=args.redteam_seeds, redteam_bases_per_seed=args.redteam_bases,
                      real_counts=real_counts, unit_synthetic=args.unit_synthetic, unit_redteam=args.unit_redteam,
                      unit_real=args.unit_real)


def _standard_documents(args: argparse.Namespace) -> bool:
    """Graines et tailles du plan enregistré / seeds and sizes of the registered plan."""
    return (tuple(args.synthetic_seeds) == spec.SYNTHETIC_SEEDS and args.synthetic_docs == spec.SYNTHETIC_DOCS_PER_SEED
            and tuple(args.redteam_seeds) == spec.REDTEAM_SEEDS
            and args.redteam_bases == spec.REDTEAM_BASES_PER_SEED)


def _default_units(args: argparse.Namespace) -> bool:
    """Tailles d'unité enregistrées : les empreintes du plan en dépendent / registered unit sizes."""
    return ((args.unit_synthetic, args.unit_redteam, args.unit_real)
            == (spec.UNIT_SYNTHETIC_DOCS, spec.UNIT_REDTEAM_BASES, spec.UNIT_REAL_DOCS))


def _is_standard(args: argparse.Namespace) -> bool:
    return _standard_documents(args) and _default_units(args)


def _refuse(fr: str, en: str) -> int:
    from tools.protocol.campaign import EXIT_REFUSED

    print(f"refus : {fr} / refused: {en}", file=sys.stderr)
    return EXIT_REFUSED


def _standard_refusal(args: argparse.Namespace) -> int | None:
    """Refus d'une campagne standard mal réglée, avant toute requête et toute lecture du paquet / early refusals."""
    if _standard_documents(args) and not _default_units(args):
        return _refuse(f"une campagne standard garde les tailles d'unité enregistrées ({spec.UNIT_SYNTHETIC_DOCS}, "
                       f"{spec.UNIT_REDTEAM_BASES}, {spec.UNIT_REAL_DOCS}) : les empreintes du plan en dépendent",
                       "a standard campaign keeps the registered unit sizes: the plan fingerprints depend on them")
    if not _is_standard(args):
        return None
    if not args.engine_id:
        return _refuse("une campagne standard nomme l'image du service (--engine-id, donnée par run-protocol.sh)",
                       "a standard campaign names the service image (--engine-id, given by run-protocol.sh)")
    if args.allow_disk_real:
        return _refuse("--allow-disk-real est réservé aux essais : les corpus réels d'une campagne standard restent "
                       "en mémoire vive", "--allow-disk-real is for trials only: a standard campaign keeps the real "
                       "corpora in RAM")
    if args.probe_docs is not None:
        return _refuse("sonde du moteur fixée pour une campagne standard", "fixed engine probe for a standard campaign")
    return None


def _pack_refusal(pack_header: dict[str, Any], standard: bool) -> int | None:
    """Paquet des corpus réels d'une campagne standard : complet, tous les corpus / complete pack, every corpus."""
    if not standard:
        return None
    split = pack_header.get("split", "all")
    if split != "all":
        return _refuse(f"paquet réduit à la moitié {split!r} : réservé aux essais",
                       f"pack reduced to the {split!r} half, trials only")
    counts = {name: info.get("docs", 0) for name, info in pack_header.get("corpora", {}).items()}
    missing = [name for name in spec.REAL_CORPORA if not counts.get(name)]
    if missing:
        return _refuse(f"corpus réels absents ou vides dans le paquet : {', '.join(missing)}",
                       "real corpora missing or empty in the pack (the index would be impossible after hours of work)")
    return None


def _read_header(args: argparse.Namespace) -> tuple[str, str] | None:
    from tools.protocol.transport import parse_local_header

    if args.token_stdin:
        return parse_local_header(sys.stdin.buffer.read(4096))
    if args.header_file:
        return parse_local_header(Path(args.header_file).read_bytes())
    return None


def _client_factory(args: argparse.Namespace, header: tuple[str, str] | None) -> Any:
    from tools.protocol.transport import RetryPolicy, ServiceClient, UnixTransport

    def make(gate: Any) -> ServiceClient:
        return ServiceClient(UnixTransport(args.socket, header), gate,
                             RetryPolicy(max_doc_wait_s=spec.MAX_DOC_RETRY_S, down_s=args.down_s))

    return make


def _params_path(work: Path) -> Path:
    return work / "plan.json"


def cmd_run(args: argparse.Namespace) -> int:
    from tools.protocol.campaign import EXIT_DONE, EXIT_REFUSED, Settings, load_state, run_campaign
    from tools.protocol.plan import check_ram_storage, read_pack
    from tools.protocol.provenance import provenance
    from tools.protocol.report import build_report, write_report

    work = Path(args.work)
    standard = _is_standard(args)
    refusal = _standard_refusal(args)
    if refusal is not None:
        return refusal
    work.mkdir(parents=True, exist_ok=True)
    header = _read_header(args)
    real = None
    real_sources: dict[str, str] = {}
    params_path = _params_path(work)
    saved = json.loads(params_path.read_text(encoding="utf-8")) if params_path.exists() else None
    if args.real:
        storage = check_ram_storage(Path(args.real), args.allow_disk_real)
        pack_header, real = read_pack(Path(args.real))
        refusal = _pack_refusal(pack_header, standard)
        if refusal is not None:
            return refusal
        split = pack_header.get("split", "all")
        real_sources = {name: info["sha256"] for name, info in pack_header["corpora"].items()}
        real_counts = {name: info["docs"] for name, info in pack_header["corpora"].items()}
        print(f"corpus réels chargés depuis / real corpora loaded from {storage}: {len(real)} corpus, "
              f"{sum(real_counts.values()):,} documents, moitié / half: {split}", file=sys.stderr)
    elif saved is not None:
        real_counts = saved["real_counts"]
    elif standard:
        print("refus : une campagne standard commence avec les corpus réels (--real) / refused: a standard campaign "
              "starts with the real corpora (--real)", file=sys.stderr)
        return EXIT_REFUSED
    else:
        real_counts = {}
    if saved is not None and saved["real_counts"] != real_counts:
        print("refus : corpus réels différents du plan enregistré / refused: real corpora differ from the saved plan",
              file=sys.stderr)
        return EXIT_REFUSED
    plan = _build_plan(args, real_counts)
    params = {"plan_id": plan.plan_id, "standard": standard, "real_counts": real_counts,
              "synthetic_seeds": list(args.synthetic_seeds), "synthetic_docs": args.synthetic_docs,
              "redteam_seeds": list(args.redteam_seeds), "redteam_bases": args.redteam_bases,
              "units": [args.unit_synthetic, args.unit_redteam, args.unit_real]}
    if saved is None:
        params_path.write_text(json.dumps(params, indent=1) + "\n", encoding="utf-8")
    elif saved["plan_id"] != plan.plan_id:
        print("refus : plan différent de celui du dossier / refused: plan differs from the work folder's",
              file=sys.stderr)
        return EXIT_REFUSED
    settings = Settings(work, threads=args.threads, hours=args.hours, engine_id=args.engine_id or None,
                        require_local=standard, tool=provenance(),
                        wipe_real=Path(args.real) if args.real and args.wipe_real_when_done else None,
                        disclosures=tuple(args.disclose))
    if args.probe_docs is not None:  # essais seulement (refusé plus haut pour un plan standard) / trials only
        settings.probe_docs = args.probe_docs
    code = run_campaign(plan, settings, _client_factory(args, header), load_label_keys(), real, real_sources)
    if code == EXIT_DONE:
        state = load_state(work)
        assert state is not None
        paths = write_report(build_report(state, plan, standard=params["standard"]), work / "results")
        print("résultats / results: " + ", ".join(str(p) for p in paths), file=sys.stderr)
    return code


def _load(work: Path) -> tuple[Any, Any, dict[str, Any]]:
    from tools.protocol.campaign import load_state
    from tools.protocol.plan import build_plan

    params = json.loads(_params_path(work).read_text(encoding="utf-8"))
    state = load_state(work)
    if state is None:
        raise SystemExit("aucun point de reprise / no checkpoint")
    unit_synthetic, unit_redteam, unit_real = params["units"]
    plan = build_plan(synthetic_seeds=tuple(params["synthetic_seeds"]),
                      synthetic_docs_per_seed=params["synthetic_docs"],
                      redteam_seeds=tuple(params["redteam_seeds"]), redteam_bases_per_seed=params["redteam_bases"],
                      real_counts=params["real_counts"], unit_synthetic=unit_synthetic, unit_redteam=unit_redteam,
                      unit_real=unit_real)
    return state, plan, params


def cmd_status(args: argparse.Namespace) -> int:
    state, plan, params = _load(Path(args.work))
    left = [u for u in plan.units if u.uid not in state.done]
    rate = state.docs / state.active_s if state.active_s else 0.0
    kinds: dict[str, int] = {}
    for unit in left:
        kinds[unit.kind] = kinds.get(unit.kind, 0) + 1
    print(json.dumps({"plan_id": state.plan_id, "standard_plan": params["standard"], "started": state.started,
                      "engine": state.engine, "units_done": len(state.done), "units_planned": len(plan.units),
                      "units_left_by_kind": kinds, "docs": state.docs, "active_seconds": round(state.active_s),
                      "docs_per_second": round(rate, 1), "throttled_seconds": round(state.throttled_s),
                      "engine_checks": state.engine_checks, "real_pack_wiped": state.real_wiped,
                      "disclosures": state.disclosures,
                      "local_principal": all(r.get("local_principal", False) for r in state.runs),
                      "retries": dict(state.retries)}, indent=1))
    return 0


def cmd_verify_engine(args: argparse.Namespace) -> int:
    """Image du service = image enregistrée au début ? (run-protocol.sh finish) / service image = recorded image?"""
    from tools.protocol.campaign import EXIT_REFUSED, load_state

    state = load_state(Path(args.work))
    if state is None:
        raise SystemExit("aucun point de reprise / no checkpoint")
    recorded = state.engine.get("image")
    match = recorded is not None and recorded == args.engine_id
    print(json.dumps({"recorded": recorded, "current": args.engine_id, "match": match}, indent=1))
    return 0 if match else EXIT_REFUSED


def cmd_report(args: argparse.Namespace) -> int:
    from tools.protocol.campaign import save_state
    from tools.protocol.report import build_report, write_report

    work = Path(args.work)
    state, plan, params = _load(work)
    if args.disclose:
        # Écart déclaré après coup (run-protocol.sh finish) : gardé dans le point de reprise, puis dans les résultats.
        # Departure disclosed afterwards: kept in the checkpoint, then in the results.
        state.disclose(tuple(args.disclose))
        save_state(state, work)
    report = build_report(state, plan, standard=params["standard"])
    if not report["campaign"]["complete"] and not args.allow_partial:
        print("campagne incomplète : --allow-partial pour un rapport intermédiaire (jamais publié) / incomplete",
              file=sys.stderr)
        return 2
    paths = write_report(report, Path(args.out) if args.out else Path(args.work) / "results")
    print("\n".join(str(p) for p in paths))
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    plan = _build_plan(args, {})
    kinds: dict[str, int] = {}
    for unit in plan.units:
        kinds[unit.kind] = kinds.get(unit.kind, 0) + unit.count
    out: dict[str, Any] = {"plan_id_without_real": plan.plan_id, "units": len(plan.units), "base_documents": kinds,
                           "synthetic_seeds": list(args.synthetic_seeds), "redteam_seeds": list(args.redteam_seeds)}
    if args.count:
        from tools.protocol.dryrun import count_plan
        from tools.protocol.provenance import plan_matches_registration

        out.update(count_plan(plan))
        if _standard_documents(args):  # tailles d'unité autres : empreintes différentes / other unit sizes: differ
            out["matches_registration"] = plan_matches_registration(out)
    print(json.dumps(out, indent=1))
    return 0


def cmd_registration(args: argparse.Namespace) -> int:
    from tools.protocol.provenance import registration

    print(json.dumps(registration(Path(args.bundle) if args.bundle else None), indent=1))
    return 0


def cmd_pack_real(args: argparse.Namespace) -> int:
    from tools.protocol.plan import write_pack

    header = write_pack(Path(args.cache), Path(args.out), split=args.split)
    print(json.dumps({"split": header["split"], **{k: v["docs"] for k, v in header["corpora"].items()}}, indent=1))
    return 0


def cmd_bundle(args: argparse.Namespace) -> int:
    from tools.protocol.bundle import build_bundle

    path, info = build_bundle(Path(args.out))
    print(json.dumps({"bundle": str(path), **info}, indent=1))
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    from tools.protocol.merge_quality import merge

    return merge(Path(args.results), Path(args.quality), force_guards=args.force_guards,
                 allow_scaled=args.allow_scaled)


def cmd_crosscheck(args: argparse.Namespace) -> int:
    from tools.protocol.crosscheck import main as crosscheck_main

    header = _read_header(args)
    return crosscheck_main(args, header)


def cmd_crosscheck_summary(args: argparse.Namespace) -> int:
    from tools.protocol.crosscheck import write_summary

    runs = {}
    for item in args.runs:
        label, _, path = item.partition("=")
        runs[label] = json.loads(Path(path).read_text(encoding="utf-8"))
    paths, verdict = write_summary(runs, Path(args.out_dir), args.date, args.engine_note)
    print("\n".join(str(p) for p in paths))
    print(json.dumps(verdict, indent=1))
    return 0 if verdict["tool_validated"] else 1


def disclose_arg(parser: argparse.ArgumentParser) -> None:
    from tools.protocol.campaign import check_disclosure

    def parse(raw: str) -> str:
        try:
            return check_disclosure(raw)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(str(exc)) from None

    parser.add_argument("--disclose", action="append", default=[], type=parse, metavar="CODE[:DÉTAIL]",
                        help="écart à déclarer publiquement, gardé dans les résultats (" + ", ".join(spec.DISCLOSURES)
                             + ") / departure to disclose publicly, kept in the results")


def utf8_streams() -> None:
    """Sorties en UTF-8 partout (console Windows en cp1252 comprise) / UTF-8 output everywhere."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(OSError, ValueError):
                reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    utf8_streams()
    parser = argparse.ArgumentParser(prog="python -m tools.protocol", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def service_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--socket", default="/run/gdprguardian/app.sock")
        token = p.add_mutually_exclusive_group()
        token.add_argument("--token-stdin", action="store_true",
                           help="ligne « X-GG-Local: <jeton> » lue sur l'entrée standard / header line on stdin")
        token.add_argument("--header-file", help="fichier d'en-tête local (root 0600) / local header file")
        p.add_argument("--down-s", type=float, default=spec.SERVICE_DOWN_S)

    p = sub.add_parser("run", help="lance ou reprend la campagne / run or resume the campaign")
    service_args(p)
    p.add_argument("--engine-id", help="image du conteneur du service (docker inspect), obligatoire pour une "
                                       "campagne standard / the service container's image, required when standard")
    p.add_argument("--real", help="paquet des corpus réels en mémoire vive / real-corpus pack in RAM storage")
    p.add_argument("--wipe-real-when-done", action="store_true",
                   help="efface le paquet dès les unités réelles enregistrées / wipes the pack once the real units "
                        "are saved")
    p.add_argument("--allow-disk-real", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--probe-docs", type=int, default=None, help=argparse.SUPPRESS)
    p.add_argument("--work", required=True, help="points de reprise et résultats (agrégats) / checkpoints, results")
    p.add_argument("--threads", type=int, default=spec.CLIENT_THREADS)
    p.add_argument("--hours", type=float, default=None, help="pause après ce temps / pause after this time")
    disclose_arg(p)
    _plan_args(p)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("status")
    p.add_argument("--work", required=True)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("verify-engine", help="image du service = image de la campagne ? / same service image?")
    p.add_argument("--work", required=True)
    p.add_argument("--engine-id", required=True)
    p.set_defaults(func=cmd_verify_engine)

    p = sub.add_parser("registration", help="empreintes à publier avant le lancement / digests to publish first")
    p.add_argument("--bundle", help="paquet .pyz à décrire aussi / .pyz bundle to describe too")
    p.set_defaults(func=cmd_registration)

    p = sub.add_parser("report")
    p.add_argument("--work", required=True)
    p.add_argument("--out")
    p.add_argument("--allow-partial", action="store_true")
    disclose_arg(p)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("plan")
    p.add_argument("--count", action="store_true", help="génère tout le plan sans service / dry run, no service")
    _plan_args(p)
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("pack-real")
    p.add_argument("--cache", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--split", choices=("all", "dev"), default="all",
                   help="dev : moitié dev seulement, pour tout essai avant la campagne / dev half only, for trials")
    p.set_defaults(func=cmd_pack_real)

    p = sub.add_parser("bundle")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_bundle)

    p = sub.add_parser("merge-quality")
    p.add_argument("results")
    p.add_argument("quality")
    p.add_argument("--force-guards", action="store_true")
    p.add_argument("--allow-scaled", action="store_true", help=argparse.SUPPRESS)
    p.set_defaults(func=cmd_merge)

    p = sub.add_parser("labels", help="régénère labels.json depuis le moteur / regenerates labels.json")
    p.set_defaults(func=cmd_labels)

    p = sub.add_parser("crosscheck")
    service_args(p)
    p.add_argument("--docs", type=int, default=540)
    p.add_argument("--mutation-docs", type=int, default=135)
    p.add_argument("--seed", type=int, default=spec.DEV_SEED)
    p.add_argument("--countries", default="auto")
    p.add_argument("--reference", default="benchmarks/results/eval-2026-10-25-standard.json")
    p.add_argument("--out", required=True)
    p.add_argument("--threads", type=int, default=spec.CLIENT_THREADS)
    p.set_defaults(func=cmd_crosscheck)

    p = sub.add_parser("crosscheck-summary", help="résumé publié des contrôles croisés / published cross-check summary")
    p.add_argument("--runs", nargs="+", required=True, help="PAYS=crosscheck.json …, par exemple auto=a.json FR=b.json")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--engine-note", required=True, help="moteur contrôlé (copie figée, empreinte) / engine checked")
    p.set_defaults(func=cmd_crosscheck_summary)

    args = parser.parse_args(argv)
    return int(args.func(args))
