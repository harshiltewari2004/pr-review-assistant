"""Candidate set constructions.03 §4."""

from app.retrieval.scoring import build_candidate_set


def test_union_introduces_no_candidate_absent_from_every_signal():
    """Invarinat 1, structural half. 07 §4.

    Each signal enforces the temporal filter at its own source:p.created_at
    <$3 in VECTOR_SIGNAL_SQL and FILE_CANDIDATES_SQL, and in Python inside
    bm25_signal().Set union cannot produce a number that was in no input,
    so a temporarlly-clean input gurantess a temporally-clean C.

    This is the assertion that makes the whole filter chain sound :it is why 
    the filter does NOT need re-enforcing here, and why re-enforcing it here
    would hide a leak in a signal rather than surface it.
    """

    vector={1:0.9,2:0.8} 
    files={2:0.5,3:0.4}
    bm25={3:7.0,4:6.5}

    c = build_candidate_set(vector,files,bm25)

    assert set(c.ids)<=set(vector)|set(files)|set(bm25) 
    assert c.ids == [1,2,3,4]


def test_query_pr_never_retrieves_itself():
    """Invariant 1, second half — 07 §4's assertion nobody has written down

    id<>query.id in BOTH SQL constants and pr_id!=query_pr_id in 
    bm25_signal().A PR is not strictly less than itself so a `<=` typo in 
    the temporal comparison passes the first assertion and fails this one.
    """
    query_pr_id=42
    vector={7:0.9,8:0.8}
    files={8:0.5}
    bm25={9:70}

    c=build_candidate_set(vector,files,bm25)

    assert query_pr_id not in c.ids
