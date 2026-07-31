#!/usr/bin/env python3
"""Day 4 — embedding sanity spike (08 §8, 09 §5). Throwaway.

Measures SEPARATION, not magnitude: similar-pair cosine minus control-pair
cosine, per repo. Absolute cosine is discarded by per-query min-max
normalization (03 §8) — only the spread survives into the ranking.

Embeds HUNKS ONLY. No titles, no bodies: that is BM25's job (03 §7), and
including it would let lexical overlap carry the number.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

# Mirrors app/retrieval/constants.py (06 §6). Duplicated, not imported:
# spikes/ runs as a script, so app/ is not on sys.path.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MAX_MODEL_TOKENS = 256
EMBEDDING_DIM = 384

# Verified from actual diffs, not titles. Fifth field is the parse variant.
PAIRS = [
    ("fastapi", "similar_a", 15994, 15992, "default"),
    ("fastapi", "similar_b_src", 15937, 15813, "source_only"),  # PRIMARY, 08 §8a
    ("fastapi", "similar_b_full", 15937, 15813, "default"),  # secondary
    ("fastapi", "control", 15992, 15515, "default"),
    ("p5js", "similar_a", 8829, 8933, "default"),
    ("p5js", "similar_b_src", 8823, 8862, "source_only"),  # variant-matched to fastapi
    ("p5js", "similar_b_full", 8823, 8862, "default"),  # keeps the test-duplicate reading
    ("p5js", "control", 8829, 8964, "default"),
]

# Flat cache with a repo prefix, as fetched.
CACHE = Path(".cache/diffs")
PREFIX = {"fastapi": "", "p5js": "p5_"}

# 03 §2 exclusions, complete. Test files are deliberately NOT here (01 §6 r5).
EXCLUDED_SUFFIXES = (".md", ".txt", ".rst", ".po", ".lock", ".svg")

HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@(.*)$")

# source_only variant only (08 §8a). NOT a 03 §2 exclusion — tests are corpus
# content, and dropping them would break p5.js Similar B's 2/6 file overlap.
TEST_PATH = re.compile(r"(^|/)tests?/|(^|/)test_|_test\.|\.test\.|\.spec\.")


def diff_path(repo: str, number: int) -> Path:
    return CACHE / f"{PREFIX[repo]}{number}.diff"


def preflight() -> None:
    """Fail before the 90-second model load, not after."""
    seen, missing = set(), []
    for repo, _role, a, b, _variant in PAIRS:
        for n in (a, b):
            if (repo, n) in seen:
                continue
            seen.add((repo, n))
            p = diff_path(repo, n)
            if p.exists():
                print(f"  {p}  {p.stat().st_size:,} bytes")
            else:
                missing.append(str(p))
    if missing:
        raise SystemExit("MISSING:\n  " + "\n  ".join(missing))
    print(f"  all {len(seen)} diffs present")


def band(gap: float) -> str:
    """09 §5's three readings. Thresholds fixed before the run — reading them
    off the output afterward would be rationalization, not measurement."""
    if gap > 0.15:
        return "> 0.15  — vector signal discriminates, proceed as 03 specifies"
    if gap >= 0.05:
        return "0.05–0.15 — weak but real, rebalance toward file overlap + BM25"
    return "< 0.05  — near-random on code diffs, rethink the vector third"


def parse_hunks(diff: str, skip_tests: bool = False) -> list[tuple[str, str]]:
    """(file_path, hunk_text) per @@ block. 03 §2.

    skip_tests is the 08 §8a source-only variant, not a 03 §2 exclusion.
    """
    out: list[tuple[str, str]] = []

    for block in re.split(r"^diff --git ", diff, flags=re.M)[1:]:
        if "Binary files" in block or "GIT binary patch" in block:
            continue
        m = re.search(r"^\+\+\+(.+)$", block, flags=re.M)
        if m is None:
            continue
        target = m.group(1).strip()
        if target == "/dev/null":
            continue
        path = target[2:] if target.startswith("b/") else target
        if path.endswith(EXCLUDED_SUFFIXES) or path.endswith("-lock.json"):
            continue
        if skip_tests and TEST_PATH.search(path):
            continue

        current: list[str] | None = None
        for line in block.splitlines():
            header = HUNK_HEADER.match(line)
            if header:
                if current:
                    out.append((path, "\n".join(current)))
                # Line numbers stripped, trailing context kept (03 §2):
                # "-120,7 +120,9" is digit noise that pollutes the embedding;
                # "def jsonable_encoder(" is the enclosing function and the
                # best context in the hunk.
                current = [header.group(1).strip()]
            elif current is not None:
                current.append(line)
        if current:
            out.append((path, "\n".join(current)))

    return out


def pair_score(emb_a: np.ndarray, emb_b: np.ndarray) -> dict:
    """All-pairs cosine between two PRs' hunks. 03 §5."""
    # Unit vectors, so the dot product IS cosine. Day 3 measured that <=> is
    # magnitude-invariant anyway — normalize_embeddings is kept for range
    # predictability into 03 §8, not because cosine needs it.

    sim = emb_a @ emb_b.T

    i, j = np.unravel_index(int(sim.argmax()), sim.shape)
    ranked = np.sort(sim.ravel())[::-1]
    return {
        "max": float(sim.max()),
        "mean_top3": float(ranked[:3].mean()),
        "argmax": (int(i), int(j)),
        "n_pairs": int(sim.size),
    }


def main() -> None:
    print("preflight — cached diffs")
    preflight()

    print(f"\nloading {MODEL_NAME} ...")
    model = SentenceTransformer(MODEL_NAME)

    loaded: dict[tuple[str, int, str], tuple[list[tuple[str, str]], np.ndarray]] = {}

    def load(repo: str, number: int, variant: str):
        key = (repo, number, variant)
        if key in loaded:
            return loaded[key]
        hunks = parse_hunks(
            diff_path(repo, number).read_text(errors="replace"),
            skip_tests=(variant == "source_only"),
        )
        if not hunks:
            raise SystemExit(f"#{number} produced ZERO hunks — check exclusions")
        texts = [h[1] for h in hunks]
        toks = [len(model.tokenizer.encode(t)) for t in texts]
        trunc = sum(t > MAX_MODEL_TOKENS for t in toks)  # invariant 9
        emb = np.asarray(
            model.encode(
                texts,
                normalize_embeddings=True,
                batch_size=32,
                show_progress_bar=False,
            )
        )
        # Golden assertion, embedding stage (07 §3) — first model output in the project.
        assert emb.shape[1] == EMBEDDING_DIM, emb.shape
        assert np.allclose(np.linalg.norm(emb, axis=1), 1.0, atol=1e-5)
        print(
            f"  #{number} [{variant}]: {len(hunks)} hunks / "
            f"{len({h[0] for h in hunks})} files · "
            f"tokens {min(toks)}–{max(toks)} (med {int(np.median(toks))}) · "
            f"truncated {trunc}/{len(toks)}"
        )
        loaded[key] = (hunks, emb)
        return loaded[key]

    print("\nparsing + embedding")
    results = {}
    for repo, role, a, b, variant in PAIRS:
        ha, ea = load(repo, a, variant)
        hb, eb = load(repo, b, variant)
        results[(repo, role)] = (pair_score(ea, eb), ha, hb, a, b)

    print("\n" + "=" * 78)
    print(f"{'repo':9s}{'pair':16s}{'MAX':>8s}{'mean3':>8s}{'n_pairs':>9s}   winning hunk")
    print("=" * 78)
    for (repo, role), (s, ha, hb, a, b) in results.items():
        i, j = s["argmax"]
        print(
            f"{repo:9s}{role:16s}{s['max']:8.4f}{s['mean_top3']:8.4f}{s['n_pairs']:9d}"
            f"   #{a} {ha[i][0]} ↔ #{b} {hb[j][0]}"
        )
        print(f"{'':50s}   A: {ha[i][1].splitlines()[0][:60]!r}")
        print(f"{'':50s}   B: {hb[j][1].splitlines()[0][:60]!r}")

    # 08 §8a — does dropping the 430-line test hunk actually move the number?
    src, full = results[("fastapi", "similar_b_src")], results[("fastapi", "similar_b_full")]
    print(
        f"\nsimilar_b test-hunk effect: MAX {src[0]['max']:.4f} (src) vs "
        f"{full[0]['max']:.4f} (full) · n_pairs {src[0]['n_pairs']} vs {full[0]['n_pairs']}"
    )

    # 09 §5's criterion is "the gap, per repo" — but it was written assuming one
    # similar pair. With two, the headline gap is the mean of Similar A and
    # Similar B (source-only for FastAPI, per 08 §8a). Fixed before the run.
    HEADLINE = {"fastapi": ("similar_a", "similar_b_src"), "p5js": ("similar_a", "similar_b_src")}

    print("\nSEPARATION (similar − control) — the number that decides D-P1-2")
    gaps, per_repo = {}, {}
    for repo in ("fastapi", "p5js"):
        ctrl = results[(repo, "control")][0]
        per_pair = {}
        for r, role in results:
            if r != repo or role == "control":
                continue
            s = results[(repo, role)][0]
            per_pair[role] = s["max"] - ctrl["max"]
            print(
                f"  {repo:9s}{role:16s} MAX {s['max'] - ctrl['max']:+.4f}"
                f"   mean3 {s['mean_top3'] - ctrl['mean_top3']:+.4f}"
            )
        # min, not mean: a strong Similar A must not mask a weak Similar B
        # (see DECISIONS D-P1-4). Locked before the run.
        gaps[repo] = min(per_pair[r] for r in HEADLINE[repo])
        per_repo[repo] = per_pair

    print("\nHEADLINE GAP (09 §5 bands, fixed before the run)")
    for repo, g in gaps.items():
        print(f"  {repo:9s}{g:+.4f}   {band(g)}")
    print("\nD-P1-2 — like-for-like by pair type (the structure the pairs were built for)")
    for label, fa, p5 in (
        ("A  zero file overlap, single hunk", "similar_a", "similar_a"),
        ("B  shared files, multi-hunk", "similar_b_src", "similar_b_src"),
    ):
        d = per_repo["p5js"][p5] - per_repo["fastapi"][fa]
        print(
            f"  {label:34s} fastapi {per_repo['fastapi'][fa]:+.4f}   "
            f"p5js {per_repo['p5js'][p5]:+.4f}   delta {d:+.4f}"
        )
    print("  → deltas disagreeing in sign = inconclusive, D-P1-2 stays OPEN")


if __name__ == "__main__":
    main()
