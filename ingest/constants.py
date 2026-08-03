"""Corpus filter constants — 01_evaluation_protocol.md §2.

The exclusion_reason literals are named here and never written inline. A typo
splits the 02_data_models.md §4 audit query
    SELECT exclusion_reason, count(*) FROM pull_requests GROUP BY 1
into two silent buckets, and the README count becomes unexplainable.
"""

import re
from pathlib import Path

# --- exclusion_reason literals -------------------------------------------
# Step 2, list metadata (04_architecture.md §5):
REASON_BOT_AUTHOR = "bot_author"
REASON_HOUSEKEEPING = "housekeeping"
REASON_DUPLICATE_RESUBMISSION = "duplicate_resubmission"

# Step 4b, content-based. Applied in the parser path, NOT in corpus_filter.py.
# Named here so all four literals live in one place for the §4 audit.
REASON_NO_SOURCE_CONTENT = "no_source_content"
# Fifth exclusion_reason literal. Applied at 04 §5 step 3, not step 2 or 4b
# (D-P2-2, resolved 2026-07-30). Match the naming shape of the other four.
REASON_DIFF_UNAVAILABLE = "diff_unavailable"
# Reachable at 04 §5 step 2 only. no_source_content fires at 4b, diff_unavailable at step 3.
STEP2_EXCLUSION_REASONS = frozenset(
    {REASON_BOT_AUTHOR, REASON_HOUSEKEEPING, REASON_DUPLICATE_RESUBMISSION}
)
ALL_EXCLUSION_REASONS = frozenset(
    {
        REASON_DUPLICATE_RESUBMISSION,
        REASON_NO_SOURCE_CONTENT,
        REASON_DIFF_UNAVAILABLE,
        REASON_BOT_AUTHOR,
        REASON_HOUSEKEEPING,
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
BOT_LOGIN_SUFFIX = "[bot]"


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
# No title-similarity threshold. D-P2-4 REVERSED 2026-08-02: a 0.95
# SequenceMatcher ratio grouped four merged, distinct PRs (#2780, #2781,
# #4409,#4369)as resubmissions - verified on github. "Near-identical"
# in 01 §2 means normalized-exact. Do not reintroduce a ratio branch
# without evidence that exact matching misses real resubmissions

# --- GitHub client (04 §5 steps 1 and 3) ---
GITHUB_API_ROOT = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"
DIFF_MEDIA_TYPE = "application/vnd.github.diff"

PER_PAGE = 100
LIST_STATE = "all"  # 02 §4's CHECK admits outcome='open' (D-P2-6)
LIST_SORT = "created"
LIST_DIRECTION = "asc"  # page-level cache resumability depends on this

INTER_REQUEST_DELAY_S = 0.75  # secondary rate limiter, independent of quota
RATE_LIMIT_FLOOR = 100
RATE_LIMIT_SLEEP_BUFFER_S = 5
MAX_BACKOFF_ATTEMPTS = 5
BACKOFF_BASE_S = 2.0

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_ROOT = REPO_ROOT / ".cache"
PR_LIST_CACHE = CACHE_ROOT / "prs"
DIFF_CACHE = CACHE_ROOT / "diffs"

GHOST_AUTHOR = "ghost"


EXPECTED_FIRST_NUMBER = 16
EXPECTED_TOTAL_LOW = 4_300
EXPECTED_TOTAL_HIGH = 4_500
