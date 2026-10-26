"""Pagination par caractères / character pagination."""

from __future__ import annotations

import itertools
import re

from hypothesis import given, settings
from hypothesis import strategies as st

from gdprguardian.server.pagination import merge_interval, page_bounds

PLACEHOLDER = re.compile(r"\[[A-Z_]+_[0-9]+\]")


def pages_of(text: str, size: int) -> list[str]:
    return [text[a:b] for a, b in itertools.pairwise(page_bounds(text, size))]


def test_short_and_empty_texts_are_one_page() -> None:
    assert page_bounds("", 1000) == [0, 0]
    assert page_bounds("abc", 1000) == [0, 3]


def test_cuts_after_a_newline() -> None:
    text = ("x" * 90 + "\n") * 30
    pages = pages_of(text, 1000)
    assert all(page.endswith("\n") for page in pages)
    assert "".join(pages) == text


def test_hard_cut_never_splits_a_placeholder() -> None:
    text = "x" * 995 + "[PERSONNE_12]" + "y" * 2000
    pages = pages_of(text, 1000)
    assert pages[0] == "x" * 995
    assert pages[1].startswith("[PERSONNE_12]")


@settings(max_examples=200, deadline=None)
@given(
    words=st.lists(st.sampled_from(["mot", "[PERSONNE_1]", "[EMAIL_23]", "\n", " ", "x" * 50, "é"]), max_size=400),
    size=st.integers(min_value=40, max_value=400),
)
def test_pages_cover_text_exactly_and_respect_size(words: list[str], size: int) -> None:
    text = "".join(words)
    pages = pages_of(text, size)
    assert "".join(pages) == text
    assert all(0 < len(page) <= size for page in pages) or text == ""
    # Une coupe recule d'un quart de page ou d'une balise au plus / a cut gives back a quarter or a placeholder.
    assert all(len(page) >= size - max(size // 4, 48) for page in pages[:-1])
    found = [m.group() for page in pages for m in PLACEHOLDER.finditer(page)]
    assert found == PLACEHOLDER.findall(text)


def test_merge_interval() -> None:
    assert merge_interval([], 0, 10) == [(0, 10)]
    assert merge_interval([(0, 10)], 20, 30) == [(0, 10), (20, 30)]
    assert merge_interval([(0, 10), (20, 30)], 10, 20) == [(0, 30)]
    assert merge_interval([(5, 8)], 0, 6) == [(0, 8)]
    assert merge_interval([], 0, 0) == [(0, 0)]


def _naive_merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for lo, hi in sorted(intervals):
        if merged and lo <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged


@settings(max_examples=300, deadline=None)
@given(st.lists(st.tuples(st.integers(0, 200), st.integers(1, 40)), max_size=60))
def test_merge_interval_matches_a_naive_union(pairs: list[tuple[int, int]]) -> None:
    served: list[tuple[int, int]] = []
    inserted: list[tuple[int, int]] = []
    for start, width in pairs:
        merge_interval(served, start, start + width)
        inserted.append((start, start + width))
        assert served == _naive_merge(inserted)
