"""Day 34: apply the D-P5-16 policy to the author's 30 measure pairs.

final = 0 if the round-1 LLM grade (batch2_claude_grades.psv) was 0,
else max(round-2 grade, 1). So eval.agreement measures exactly the labels
the database will hold. Writes eval/artifacts/round2_policy_measure.psv.

Usage: python -m scripts.day34_policy_grades
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from eval.agreement import ARTIFACTS, HUMAN_PATH, LLM_PATH, read_grades

ROUND2_PATH = ARTIFACTS / "round2_claude_grades.psv"
OUT_PATH = ARTIFACTS / "round2_policy_measure.psv"


def read_rows(path: Path) -> dict[tuple[int, int], tuple[int, str]]:
    out = {}
    for line in path.read_text().splitlines():
        if line.strip():
            q, c, g, reason = line.split("|", 3)
            out[(int(q), int(c))] = (int(g), reason.strip())
    return out


def main() -> None:
    measure = sorted(read_grades(HUMAN_PATH))
    round1 = read_rows(LLM_PATH)
    round2 = read_rows(ROUND2_PATH)
    assert all(k in round1 and k in round2 for k in measure), "measure pair missing"

    lines, outcomes = [], Counter()
    for q, c in measure:
        g1, why1 = round1[(q, c)]
        g2, why2 = round2[(q, c)]
        if g1 == 0:
            grade, why, outcome = 0, "", "round-1 zero kept"
        elif g2 == 0:
            grade, why, outcome = 1, why1, "round-2 zero rejected"
        else:
            grade, why, outcome = g2, why2, "round-2 accepted"
        outcomes[outcome] += 1
        lines.append(f"{q}|{c}|{grade}|{why}")

    OUT_PATH.write_text("\n".join(lines) + "\n")
    print(
        f"wrote {OUT_PATH.name}: {len(lines)} pairs  "
        + ", ".join(f"{k} {v}" for k, v in sorted(outcomes.items()))
    )


if __name__ == "__main__":
    main()
