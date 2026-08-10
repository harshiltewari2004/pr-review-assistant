"""Chunking tests. 07 §4 invariants, golden assertion per 07 §3.

Counts are transcribed from observed output, not predicted. No test asserts
retrieval quality (07 §1).
"""

import re
from pathlib import Path

from app.retrieval.chunking import Hunk, diff_totals, files_changed, is_excluded, parse_hunks

FIXTURES = Path(__file__).parent.parent / "fixtures" / "diffs"

HEADER_NUMBERS = re.compile(r"-\d+(?:,\d+)? \+\d+(?:,\d+)? @@")


def load(name: str) -> str:
    return (FIXTURES / f"{name}.diff").read_text()


# --- golden assertion, 07 §3 ------------------------------------------------


def test_golden_simple_single_file():
    hunks = parse_hunks(load("simple_single_file"))
    assert len(hunks) == 1
    assert hunks[0].file_path == "fastapi/utils.py"
    assert not HEADER_NUMBERS.search(hunks[0].content)


# --- header handling, 03 §2 -------------------------------------------------


def test_trailing_context_is_retained():
    hunks = parse_hunks(load("simple_single_file"))
    assert hunks[0].content.splitlines()[0].startswith("def get_value_or_default(")


def test_at_marker_in_content_does_not_split():
    hunks = parse_hunks(load("at_marker_in_content"))
    assert len(hunks) == 1


# --- zero-hunk cases, 07 §4 -------------------------------------------------


def test_deleted_files_produce_no_hunks():
    assert parse_hunks(load("deleted_file")) == []


def test_rename_only_produces_no_hunks():
    assert parse_hunks(load("rename_only")) == []


def test_empty_diff_does_not_raise():
    assert parse_hunks("") == []


def test_binary_block_produces_no_hunks():
    # Four blocks, one binary; README.md excluded; two .yml survive.
    hunks = parse_hunks(load("binary_file"))
    assert files_changed(hunks) == [
        "docs/en/data/sponsors.yml",
        "docs/en/data/sponsors_badge.yml",
    ]


# --- file exclusions, 03 §2 -------------------------------------------------


def test_md_excluded_inside_in_corpus_pr():
    hunks = parse_hunks(load("md_excluded"))
    assert files_changed(hunks) == ["fastapi/__init__.py"]


def test_translation_payload_excluded_loader_is_not():
    # 03 §2: the exclusion is on the payloads, not the directory.
    assert is_excluded("translations/es/translation.json")
    assert not is_excluded("translations/dev.js")
    assert not is_excluded("translations/index.js")


def test_excluded_extensions():
    for path in ("a/b.md", "CHANGELOG.txt", "x.svg", "package-lock.json"):
        assert is_excluded(path), path
    for path in ("src/webgl/p5.Shader.js", "a.py", "b.json"):
        assert not is_excluded(path), path


# --- hunk_index, 07 §4 ------------------------------------------------------


def test_hunk_index_is_sequential_per_file():
    hunks = parse_hunks(load("huge_hunk"))
    assert len(hunks) == 23
    per_file: dict[str, list[int]] = {}
    for h in hunks:
        per_file.setdefault(h.file_path, []).append(h.hunk_index)
    assert per_file == {
        "fastapi/dependencies/models.py": [0, 1, 2],
        "fastapi/dependencies/utils.py": list(range(11)),
        "fastapi/openapi/utils.py": [0, 1],
        "fastapi/routing.py": list(range(6)),
        "tests/test_dependency_models.py": [0],
    }


# --- D-P2-14 ----------------------------------------------------------------


def test_files_changed_is_paths_that_produced_hunks():
    hunks = parse_hunks(load("huge_hunk"))
    assert files_changed(hunks) == sorted({h.file_path for h in hunks})


def test_diff_totals_are_source_only():
    hunks = parse_hunks(load("huge_hunk"))
    assert diff_totals(hunks) == (447, 167)


def test_hunk_carries_no_token_fields():
    # D-P2-19: token_count / was_truncated are stamped at the embedding stage.
    assert not hasattr(Hunk("a", 0, "", 0, 0), "token_count")


def test_generated_files_excluded_through_parse_hunks():
    hunks = parse_hunks(load("generated_excluded"))
    assert [h.file_path for h in hunks] == ["src/core/main.js"]
