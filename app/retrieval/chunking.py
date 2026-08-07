"""Diff → hunks. Governed by 03_retrieval_engine.md §2.

Pure text processing: no model, no database, no network. A Hunk is transient
(06 §2) — it becomes a chunk only when store_chunks() persists it, which is
where pr_id and repo_id are attached (D-P2-19).

token_count and was_truncated are NOT set here; they require the MiniLM
tokenizer and are stamped at pipeline step 5 (D-P2-19).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# --- file-level exclusions, 03 §2 -------------------------------------------

EXCLUDED_EXTENSIONS = frozenset({".md", ".txt", ".rst", ".po", ".lock", ".svg"})

EXCLUDED_BASENAMES = frozenset({"package-lock.json"})

# 03 §2: the exclusion is on the PAYLOADS, not the directory.
# translations/dev.js and translations/index.js are the i18next loader and
# are ordinary source. Only translations/<locale>/translation.json is data.
TRANSLATION_PAYLOAD = re.compile(r"^translations/[^/]+/translation\.json$")

# --- diff structure ---------------------------------------------------------

_FILE_BLOCK = re.compile(r"^diff --git ", re.MULTILINE)
_NEW_PATH = re.compile(r"^\+\+\+ (?:b/)?(.+)$", re.MULTILINE)
_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@(.*)$", re.MULTILINE)


@dataclass(frozen=True)
class Hunk:
    file_path: str
    hunk_index: int
    content: str
    additions: int
    deletions: int


def files_changed(hunks: list[Hunk]) -> list[str]:
    """D-P2-14: files_changed is exactly the paths that produced a hunk."""
    return sorted({h.file_path for h in hunks})


def diff_totals(hunks: list[Hunk]) -> tuple[int, int]:
    """D-P2-14: source-only totals. Will NOT match GitHub's PR page."""
    return sum(h.additions for h in hunks), sum(h.deletions for h in hunks)


def is_excluded(path: str) -> bool:
    """03 §2 file-level exclusions."""
    basename = path.rsplit("/", 1)[-1]
    if basename in EXCLUDED_BASENAMES:
        return True
    if TRANSLATION_PAYLOAD.match(path):
        return True
    dot = basename.rfind(".")
    return dot != -1 and basename[dot:] in EXCLUDED_EXTENSIONS


def _new_path(header_region: str) -> str | None:
    """Path from `+++b/<path>`.None means:emit no hunks for this block."""
    match = _NEW_PATH.search(header_region)
    if match is None:
        return None
    path = match.group(1).strip()
    if path == "/dev/null":
        return None
    return path


def parse_hunks(diff: str) -> list[Hunk]:
    hunks: list[Hunk] = []

    for block in _FILE_BLOCK.split(diff)[1:]:
        first = _HUNK_HEADER.search(block)
        if first is None:
            continue

        path = _new_path(block[: first.start()])
        if path is None or is_excluded(path):
            continue

        parts = _HUNK_HEADER.split(block)
        for index, (context, body) in enumerate(zip(parts[1::2], parts[2::2])):
            lines = body.splitlines()
            hunks.append(
                Hunk(
                    file_path=path,
                    hunk_index=index,
                    content=_render(context, body),
                    additions=sum(1 for ln in lines if ln.startswith("+")),
                    deletions=sum(1 for ln in lines if ln.startswith("-")),
                )
            )

    return hunks


def _render(context: str, body: str) -> str:
    """03 §2: line numbers stripped, trailing context retained."""
    context = context.strip()
    body = body.strip("\n")
    return f"{context}\n{body}" if context else body
