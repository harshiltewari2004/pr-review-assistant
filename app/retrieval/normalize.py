"""Per-query min-max normalization. 03 §8.

Raw signal values are computed in signals.py; the weighted sum is in
scoring.py. This module does one thing so that the one thing is testable.
"""

from __future__ import annotations


def min_max_normalize(
    raw: dict[int, float],
    candidate_ids: list[int],
) -> dict[int, float]:
    """Raw scores ->[0,1]over candidate_ids per query. 03 §8.

    candidate_ids is passed EXPLICITLY rather than inferred from raw.keys().
    Invariant 2 requires all three signals normalized over the same
    population; inferring it would let each signal normalize over its own
    keys, which is that invariant failing with no error anywhere.Passing C
    in makes a mismatch raise instead.

    Degenerate case:max==min returns 0.0 for evvery candidate (invariant
    4).Not 1.0 and not 0.5 - a signal with no spread carries no ranking
    information for this query , and 0.0 is the value that lets its weight
    contribute nothing rather than contributing a constant.
    """

    if not candidate_ids:
        raise ValueError("candidate_ids is empty; nothing to normalize")

    missing = set(candidate_ids) - set(raw)
    if missing:
        raise ValueError(
            f"raw is missing {len(missing)}of {len(candidate_ids)}candidates: "
            f"{sorted(missing)[:5]}-03 §4 step 6 backfill did not run"
        )

    values = [raw[pr_id] for pr_id in candidate_ids]

    lo, hi = min(values), max(values)

    if hi == lo:
        return {pr_id: 0.0 for pr_id in candidate_ids}

    span = hi - lo
    return {pr_id: (raw[pr_id] - lo) / span for pr_id in candidate_ids}
