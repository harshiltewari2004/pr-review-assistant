from collections import Counter
from datetime import UTC, datetime, timedelta

from ingest.constants import (
    REASON_BOT_AUTHOR,
    REASON_DUPLICATE_RESUBMISSION,
    REASON_HOUSEKEEPING,
)
from ingest.corpus_filter import (
    PRMeta,
    apply_corpus_filter,
    classify,
    normalize_title,
    titles_match,
)

BASE = datetime(2026, 3, 1, tzinfo=UTC)


def _pr(number, title, author, author_type="User", day=0, merged=False):
    created = BASE + timedelta(days=day)
    return PRMeta(number, title, author, author_type, created, created if merged else None)


FIXTURES = [
    _pr(9001, "Bump rollup from 4.1.0 to 4.2.0", "dependabot[bot]", "Bot"),
    _pr(9002, "chore: update contributors.png", "maintainer-a"),
    _pr(9003, "docs: clarify createCanvas parameters", "contrib-a"),  # 4b catches this
    _pr(9004, "Fix stroke weight and document the change", "contrib-b"),  # docs + code, stays
    _pr(8945, "Fix textAlign regression in WEBGL", "contrib-c", day=0),
    _pr(8946, "Fix textAlign regression in WEBGL", "contrib-c", day=1, merged=True),
    _pr(8947, "Fix textAlign regression in WEBGL", "contrib-c", day=2),
    _pr(9005, "Regenerate contributor table", "allcontributors", "User"),  # bot-shaped 'User'
]


def test_golden_breakdown():
    verdicts = {v.number: v for v in apply_corpus_filter(FIXTURES)}

    assert verdicts[9001].exclusion_reason == REASON_BOT_AUTHOR
    assert verdicts[9005].exclusion_reason == REASON_BOT_AUTHOR
    assert verdicts[9002].exclusion_reason == REASON_HOUSEKEEPING

    assert verdicts[9003].in_corpus is True
    assert verdicts[9004].in_corpus is True

    kept = [n for n in (8945, 8946, 8947) if verdicts[n].in_corpus]
    assert kept == [8946]
    assert verdicts[8945].exclusion_reason == REASON_DUPLICATE_RESUBMISSION
    assert verdicts[8947].exclusion_reason == REASON_DUPLICATE_RESUBMISSION

    for v in verdicts.values():
        assert (v.exclusion_reason is None) == v.in_corpus

    print(Counter(v.exclusion_reason for v in verdicts.values()))


def test_account_list_catches_suffixed_login_reported_as_user():
    """07 §4: a bot-shaped account GitHub reports as author_type='User' must
    still be excluded. Real logins carry '[bot]'; 01 §2's list does not.
    """
    pr = PRMeta(
        number=9001,
        title="Bump lodash from 4.17.20 to 4.17.21",
        author="dependabot[bot]",
        author_type="User",  # the rule under test, NOT 'Bot'
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        merged_at=None,
    )
    assert classify(pr) == REASON_BOT_AUTHOR


def test_high_ratio_titles_do_not_group():
    """D-P2-4, reversed 2026-08-02. These two differ by one character and
    score 0.9688 on SequenceMatcher — over the 0.95 threshold that used to
    live in constants.py. They are separate issues and separate work. The
    ratio branch grouped four merged p5.js PRs this way (#2780/#2781,
    #4409/#4369); nothing in the suite caught it. This is that test.
    """
    a = _pr(9101, "Fix #8901:stroke weight ignored", "contrib-d", day=0)
    b = _pr(9102, "Fix #8902:stroke weight ignored", "contrib-d", day=1)

    assert not titles_match(a.title, b.title)

    verdicts = {v.number: v for v in apply_corpus_filter([a, b])}
    assert verdicts[9101].in_corpus is True
    assert verdicts[9102].in_corpus is True


def test_normalize_title_leaves_no_trailing_space_after_punctuation_strip():
    """Punctuation is stripped after whitespace collapse (D-P2-4), so a title
    ending ' .' would otherwise keep a trailing space and fail the comparison.
    Since D-P2-4 was reversed, exact match is the ONLY branch — normalization
    is now the whole of duplicate detection, not a fast path before a ratio
    fallback. Documented failure mode, pinned here."""
    assert normalize_title("Fix the bug .") == "fix the bug"
    assert normalize_title("Fix   the   bug .") == normalize_title("Fix the bug")
