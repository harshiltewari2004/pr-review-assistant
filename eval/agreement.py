"""Human-vs-LLM label agreement (D-P5-14, 01 §12).

Compares the author's blind grades on the 30-pair batch-2 subset with the
fresh-context Claude grades for the same pairs. Reads two committed .psv
files (query#|candidate#|grade|reason), so it runs offline and is
reproducible. Reports, each with a percentile bootstrap 95% CI:
  three_grade  unweighted Cohen's kappa over {0, 1, 2} (01 §12 item 4)
  lenient_ge1  binary kappa at grade >= 1 (backs lenient Recall@3)
  strict_eq2   binary kappa at grade == 2 (backs strict Recall@3)
  qwk          quadratic weighted kappa over {0, 1, 2} (01 §12, ordinal scale)
plus the confusion matrix and the disagreeing pairs. Writes
eval/artifacts/agreement_batch2.json.

Usage: python -m eval.agreement
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable
from pathlib import Path

ARTIFACTS = Path(__file__).parent / "artifacts"
HUMAN_PATH = ARTIFACTS / "batch2_author_subset.psv"
LLM_PATH = ARTIFACTS / "batch2_claude_grades.psv"
OUT_PATH = ARTIFACTS / "agreement_batch2.json"

GRADES = (0, 1, 2)
KAPPA_THRESHOLD = 0.6  # 01 §12
BOOTSTRAP_ROUNDS = 10_000
SEED = 32

Stat = Callable[[list[int], list[int], tuple[int, ...]], float]


def read_grades(path: Path) -> dict[tuple[int, int], int]:
    out = {}
    for line in path.read_text().splitlines():
        if line.strip():
            q, c, g, _ = line.split("|", 3)
            out[(int(q), int(c))] = int(g)
    return out


def cohen_kappa(a: list[int], b: list[int], labels: tuple[int, ...]) -> float:
    """(observed - chance) / (1 - chance). Chance = sum over labels of p_a * p_b."""
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b, strict=True)) / n
    chance = sum((a.count(k) / n) * (b.count(k) / n) for k in labels)
    if chance == 1.0:
        return 1.0  # both raters used one label throughout, so observed is 1 too
    return (observed - chance) / (1 - chance)


def quadratic_weighted_kappa(a: list[int], b: list[int], labels: tuple[int, ...]) -> float:
    """1 - weighted observed disagreement / weighted chance disagreement.

    Weight (i - j)^2 / (max - min)^2: a 2-vs-0 miss costs 4x a 2-vs-1 miss.
    """
    n = len(a)
    span = (max(labels) - min(labels)) ** 2
    observed = sum((x - y) ** 2 for x, y in zip(a, b, strict=True)) / (n * span)
    chance = sum(a.count(i) * b.count(j) * (i - j) ** 2 for i in labels for j in labels) / (
        n * n * span
    )
    if chance == 0.0:
        return 1.0  # both raters used one identical label throughout
    return 1 - observed / chance


def bootstrap_ci(
    a: list[int], b: list[int], labels: tuple[int, ...], stat: Stat, rng: random.Random
) -> tuple[float, float]:
    """Resample pairs with replacement; 2.5th and 97.5th percentile of stat."""
    n = len(a)
    stats = []
    for _ in range(BOOTSTRAP_ROUNDS):
        idx = [rng.randrange(n) for _ in range(n)]
        stats.append(stat([a[i] for i in idx], [b[i] for i in idx], labels))
    stats.sort()
    return stats[int(0.025 * BOOTSTRAP_ROUNDS)], stats[int(0.975 * BOOTSTRAP_ROUNDS) - 1]


def main() -> None:
    human = read_grades(HUMAN_PATH)
    llm = read_grades(LLM_PATH)
    missing = set(human) - set(llm)
    assert not missing, f"{len(missing)} subset pairs missing from the LLM grades"

    pairs = sorted(human)
    h = [human[p] for p in pairs]
    m = [llm[p] for p in pairs]
    n = len(pairs)
    rng = random.Random(SEED)

    # Order matters: the shared rng makes each view's CI depend on the views before it.
    views: dict[str, tuple[list[int], list[int], tuple[int, ...], Stat]] = {
        "three_grade": (h, m, GRADES, cohen_kappa),
        "lenient_ge1": ([int(x >= 1) for x in h], [int(x >= 1) for x in m], (0, 1), cohen_kappa),
        "strict_eq2": ([int(x == 2) for x in h], [int(x == 2) for x in m], (0, 1), cohen_kappa),
        "qwk": (h, m, GRADES, quadratic_weighted_kappa),
    }
    results = {}
    for name, (a, b, labels, stat) in views.items():
        kappa = stat(a, b, labels)
        lo, hi = bootstrap_ci(a, b, labels, stat, rng)
        agree = sum(x == y for x, y in zip(a, b, strict=True))
        results[name] = {
            "kappa": round(kappa, 4),
            "ci95": [round(lo, 4), round(hi, 4)],
            "agreement": f"{agree}/{n}",
        }
        print(f"{name:12} kappa {kappa:.3f}  95% CI [{lo:.3f}, {hi:.3f}]  raw {agree}/{n}")

    confusion = [
        [sum(x == i and y == j for x, y in zip(h, m, strict=True)) for j in GRADES] for i in GRADES
    ]
    print("\nconfusion (rows = author, cols = Claude):")
    print("        C0  C1  C2")
    for i, row in zip(GRADES, confusion, strict=True):
        print(f"  A{i}  " + "".join(f"{v:4d}" for v in row))

    disagreements = [
        {"query": q, "candidate": c, "author": human[(q, c)], "claude": llm[(q, c)]}
        for q, c in pairs
        if human[(q, c)] != llm[(q, c)]
    ]
    print(f"\ndisagreements: {len(disagreements)}")
    for d in disagreements:
        print(f"  #{d['query']} <- #{d['candidate']}: author {d['author']}, claude {d['claude']}")

    passed = results["three_grade"]["kappa"] >= KAPPA_THRESHOLD
    verdict = "PASS" if passed else "FAIL -> stop before Phase 6"
    print(f"\n01 §12 threshold {KAPPA_THRESHOLD} (three_grade): {verdict}")

    OUT_PATH.write_text(
        json.dumps(
            {
                "n": n,
                "seed": SEED,
                "bootstrap_rounds": BOOTSTRAP_ROUNDS,
                "threshold": KAPPA_THRESHOLD,
                "passed": passed,
                "views": results,
                "confusion_rows_author_cols_claude": confusion,
                "disagreements": disagreements,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
