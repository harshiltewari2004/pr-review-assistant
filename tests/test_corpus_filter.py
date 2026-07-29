from collections import counter
from datetime import datetime,timedelta,timezone

from ingest.constants import(
    REASON_BOT_AUTHOR,
    REASON_DUPLICATE_RESUBMISSION,
    REASON_HOUSEKEEPING,
)

from ingest.corpus_filter import PRMeta, apply_corpus_filter

BASE = datetime(2026,3,1,tzinfo=timezone.utc)

def _pr(number,title,author,author_type="User",day=0,merged=False):
    created = BASE+timedelta(days=day)
    return PRMeta(number,title,author,author_type,created,created if merged else None)


FIXTURES = [
    _pr(9001, "Bump rollup from 4.1.0 to 4.2.0", "dependabot[bot]", "Bot"),
    _pr(9002, "chore: update contributors.png", "maintainer-a"),
    _pr(9003, "docs: clarify createCanvas parameters", "contrib-a"),          # 4b catches this
    _pr(9004, "Fix stroke weight and document the change", "contrib-b"),      # docs + code, stays
    _pr(8945, "Fix textAlign regression in WEBGL", "contrib-c", day=0),
    _pr(8946, "Fix textAlign regression in WEBGL", "contrib-c", day=1, merged=True),
    _pr(8947, "Fix textAlign regression in WEBGL", "contrib-c", day=2),
    _pr(9005, "Regenerate contributor table", "allcontributors", "User"),     # bot-shaped 'User'
]

def test_golden_breakdown():
    verdicts = {v.number:v for v in apply_corpus_filter(FIXTURES)}

    assert verdicts[9001].exclusion_reason == REASON_BOT_AUTHOR
    assert verdicts[9005].exclusion_reason == REASON_BOT_AUTHOR
    assert verdicts[9002].exclusion_reason == REASON_HOUSEKEEPING


    assert verdicts[9003].in_corpus is True
    assert verdicts[9004].in_corpus is True

    kept =[n for n in(8945,8946,8947)if verdicts[n].in_corpus]
    assert kept == [8946]
    assert verdicts[8945].exclusion_reason == REASON_DUPLICATE_RESUBMISSION
    assert verdicts[8947].exclusion_reason == REASON_DUPLICATE_RESUBMISSION


    for v in verdicts.values():
        assert(v.exclusion_reason is None) == v.in_corpus

    print(Counter(v.exclusion_reason for v in verdicts.values()))
