"""from_list_item contract — 07_testing.md §3.

The stage's golden assertion (page 1 = #16 -> #335, ascending, tz-aware) runs
against the network. This pins the same shape against a committed payload so
it survives offline and cannot regress silently.
"""

from __future__ import annotations

import copy
import json
from dataclasses import fields
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ingest.constants import GHOST_AUTHOR
from ingest.corpus_filter import PRMeta
from ingest.github_client import _parse_ts, from_list_item

FIXTURE = Path(__file__).parents[1] / "fixtures" / "list_items.json"


@pytest.fixture(scope="module")
def _items() -> list[dict]:
    return json.loads(FIXTURE.read_text())


@pytest.fixture
def merged_item(_items) -> dict:
    return copy.deepcopy(_items[0])  # deepcopy: tests mutate


@pytest.fixture
def unmerged_item(_items) -> dict:
    return copy.deepcopy(_items[1])


def test_prmeta_shape_is_exactly_these_six_fields():
    """PRMeta's field order moved twice this week. This pins it.

    Also fails if additions/deletions are ever added: they are NOT in the
    /pulls list payload and must be derived from the parsed diff at
    04_architecture.md §5 step 4, never from a re-fetch.
    """
    assert [f.name for f in fields(PRMeta)] == [
        "number",
        "title",
        "author",
        "author_type",
        "created_at",
        "merged_at",
    ]


def test_every_field_routes_from_the_right_key(merged_item):
    meta = from_list_item(merged_item)
    assert meta.number == merged_item["number"]
    assert meta.title == merged_item["title"]
    assert meta.author == merged_item["user"]["login"]
    assert meta.author_type == merged_item["user"]["type"]
    assert meta.created_at.isoformat().startswith(merged_item["created_at"][:19])
    assert meta.merged_at.isoformat().startswith(merged_item["merged_at"][:19])


def test_timestamps_are_tz_aware_utc(merged_item):
    """A naive datetime raises inside corpus_filter's 7-day window comparison."""
    meta = from_list_item(merged_item)
    for ts in (meta.created_at, meta.merged_at):
        assert ts.tzinfo is not None
        assert ts.utcoffset() == timedelta(0)


def test_deleted_account_becomes_ghost(merged_item):
    """GitHub sends "user": null on PRs from deleted accounts."""
    merged_item["user"] = None
    meta = from_list_item(merged_item)
    assert meta.author == GHOST_AUTHOR
    assert meta.author_type == "User"  # a deleted account is not a bot


def test_explicitly_null_login_also_becomes_ghost(merged_item):
    """The OTHER null shape. .get(key, default) fires on a MISSING key only —
    a present-but-null login returns None and blows up in classify().lower().
    """
    merged_item["user"] = {"login": None, "type": None}
    meta = from_list_item(merged_item)
    assert meta.author == GHOST_AUTHOR
    assert meta.author_type == "User"


def test_merged_at_is_none_when_never_merged(unmerged_item):
    assert unmerged_item.get("merged_at") is None
    assert from_list_item(unmerged_item).merged_at is None


def test_parse_ts_passes_none_through():
    assert _parse_ts(None) is None


def test_parse_ts_accepts_trailing_z():
    assert _parse_ts("2026-07-29T14:02:11Z") == datetime(2026, 7, 29, 14, 2, 11, tzinfo=UTC)
