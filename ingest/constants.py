"""Corpus filter constants — 01_evaluation_protocol.md §2.

The exclusion_reason literals are named here and never written inline. A typo
splits the 02_data_models.md §4 audit query
    SELECT exclusion_reason, count(*) FROM pull_requests GROUP BY 1
into two silent buckets, and the README count becomes unexplainable.
"""

import re

# --- exclusion_reason literals -------------------------------------------
# Step 2, list metadata (04_architecture.md §5):
REASON_BOT_AUTHOR = "bot_author"
REASON_HOUSEKEEPING = "housekeeping"
REASON_DUPLICATE_RESUBMISSION = "duplicate_resubmission"

# Step 4b, content-based. Applied in the parser path, NOT in corpus_filter.py.
# Named here so all four literals live in one place for the §4 audit.
REASON_NO_SOURCE_CONTENT = "no_source_content"

ALL_EXCLUSION_REASONS = frozenset(
    {
        REASON_BOT_AUTHOR,
        REASON_HOUSEKEEPING,
        REASON_DUPLICATE_RESUBMISSION,
        REASON_NO_SOURCE_CONTENT,
    }
)

# --- rule 1: bots ---------------------------------------------------------
# author_type == 'Bot' is the PRIMARY rule, so a new bot account is caught
# without a code change. This list is ADDITIVE, for accounts GitHub reports
# as 'User' (07_testing.md §4).
BOT_ACCOUNTS = frozenset(
    {
        "p5js-bot",
        "github-actions",
        "github-actions[bot]",
        "allcontributors",
        "allcontributors[bot]",
        "dependabot",
        "dependabot[bot]",
    }
)

# --- rule 2: maintainer housekeeping --------------------------------------
# Transcribed from 01 §2 exactly as written, INCLUDING case. See D-P2-5:
# widening to IGNORECASE is a change to a locked rule, so instead we log
# case-only near-misses and read them after the first full fetch.
HOUSEKEEPING_TITLE_PATTERNS = (
    re.compile(r"chore:\s*update contributors\.png"),
    re.compile(r"chore:\s*update README table from stewards\.yml"),
    re.compile(r"(update|Update) stewards\.yml"),
)

# --- rule 3: duplicate resubmissions --------------------------------------
DUPLICATE_WINDOW_DAYS = 7
TITLE_SIMILARITY_THRESHOLD = 0.95  # D-P2-4 — operationalizes "near-identical"