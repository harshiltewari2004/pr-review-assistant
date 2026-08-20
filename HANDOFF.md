# Handoff — 2026-08-20, Day 21 close (09 Day 18 COMPLETE — Milestone A met)

## Done and committed
- app/retrieval/signals.py: VectorAggregate (score_raw + chunk_hits),
  aggregate_chunk_scores() pure, vector_signal_for_pr() async orchestrator.
  Pure/IO split so aggregation is unit-testable without a DB.
  chunk_hits exists because a candidate absent from a chunk's top-50 did
  NOT score zero — it scored below that list's cutoff. Evidence count, not
  imputation.
- app/retrieval/constants.py: VECTOR_AGGREGATION="max", MEAN_TOP_K=3.
- tests/unit/test_aggregation.py: 8 tests. Tests: 43 passing.
- spikes/day18_aggregation.py: read-only, 3 golden assertions.
- Tagged v0.1-vector-only. MILESTONE A MET.
- D-P4-1 RESOLVED: no Phase 4 cut. D-P3-3 RESOLVED: mean-of-top-3 at
  query-chunk level.

## NEXT SESSION STARTS HERE
1. `git status` clean, `pytest tests/unit -q` = 43, `docker compose up -d`.
   `set -a && source .env && set +a && echo ${#DATABASE_URL_DIRECT}` → 140.
2. **09 Day 21 + Day 22 in ONE session — Jaccard AND BM25.** Merged per
   D-P4-1. Jaccard is ~10 lines against 07 §4's four assertions; it is not
   a day. BM25 is the real work: 03 §7 document construction
   (title + body + basenames) and tokenization keeping BOTH whole
   identifiers and sub-tokens.
3. **Re-run day18_aggregation against a REAL cluster PR** (FES, p5.strands,
   WebGL, Vector/Math, image/colour, framebuffer, output). #9032 is a
   workflow-YAML PR; YAML is near-duplicate text and produced 0.9945
   cosines. Those numbers do not generalize and must not be quoted.
4. Run day18_aggregation against `neon`. Everything so far is Docker/macOS.

## Fallback ladder — decided at Day 21 open, do not re-decide mid-session
- If Day 22 overruns: cut the Milestone A write-up (tag already applied).
- If Day 23 overruns: ship BM25 whole-identifier tokenization only, no
  sub-token splitting. Fails 07 §4's jsonable_encoder assertion — the loss
  is visible and tested, not silent. Restore before Day 34.
- Day 24: cut NOTHING. Temporal filter test lands.

## Measured — Day 18 (query #9032, local)
- 14 query chunks → 138 distinct candidates. Ceiling if disjoint: 700.
  Lists overlap heavily; one PR's chunks are semantically similar.
- Fan-out 920 ms / 14 chunks = 66 ms/chunk at VECTOR_TOP_K=50, localhost,
  EXCLUDING request-time embedding. Day 17's 48 ms/chunk used the spike's
  display TOP_K=10. **D-P2-24's ~630 ms worst case is superseded by ~920 ms.**
- chunk_hits: 53 of 138 (38%) seen in exactly one chunk's top 50; only 9
  seen in all 14. Cutoff bias, quantified.
- max vs mean_top_k: 8/10 top-10 overlap. Distinct scores in top 10: 8/10.
- Temporal filter: 0 leaks over the full 138-candidate union.

## Open loops
- **Ties (D-P6-1).** #8620/#8650 at +0.9445 (resubmission pair, benign).
  #7810/#7906 at +0.7899 — UNRELATED titles, identical to 4dp. Suspect a
  byte-identical shared chunk. Diagnostic: compare chunk bodies of tied
  PRs. If boilerplate chunks generate ties corpus-wide it is a chunking
  finding, not a tie-breaking one.
- Deterministic rank ordering: when scoring.py sorts, key is
  (-score, pr_id). Dict insertion order currently depends on which query
  chunk surfaced a candidate first — reproducibility hazard.
- `day17_vector_query.py` applies OFFSET 1600 to both ASC and DESC. The
  recorded "newest PR / 3,195 candidates" may not reproduce from it.
- `ON CONFLICT DO NOTHING` verification still unrun.
- 09 Day 15 `docker stats` container memory still owed. 512 MiB vs 1 GiB.
- Cloud Run is CPU-only x86. Never carry 39 chunks/s (MPS) or 5/s (Neon).
- test_embedding.py in tests/unit costs ~10 s. Move or accept.
- index_repo.py prints `no_source_content 470 predicted 220` every run.
- Local DB 147 MB vs Neon 133 MB — dead tuples. VACUUM FULL. Cite Neon.
- README owes: no_source_content 470 (12.8%), truncation 23.3% (02 §5).
- Fixture misses .map/.obj/.mtl/.stl exclusions (30 appearances).
- `build_all_rows` reaches `gh._diff_cache_path`. Private-attribute debt.
- 12 Day-4 spike diffs still use the unreachable naming scheme.
- zsh: bare SQL is not a command. Always `psql "$URL" -c "..."`.

## Retired
- Day 17's "#4132 Test pr outranks real workflow PRs" is NOT a MAX
  weakness. It was an artifact of the spike printing one chunk's ranking.
  Aggregated over 14 chunks it sits at rank 29/138 (0.7083, hits 10) while
  the top five all have hits 14/14. Use the CORRECTED version in the
  Phase 6 write-up: the apparent weakness was a measurement artifact,
  found by aggregating properly.

## Doc 12
- chunking.py COMPLETE (Day 14). No lag.
- signals.py has 1 of 3 signals. Ritual owed at Phase 4 close, not now.
- Remaining: normalize.py, signals.py, scoring.py, reasons.py,
  eval/pool.py, eval/score.py.

## Schedule
- Day 21 closed. Phase 3 COMPLETE. Phase 4 starts next session.
- Day 22: Jaccard + BM25. Day 23: union candidate set + weighted sum.
- **Day 24 HARD deadline: temporal filter test (07 §9).** Binding
  constraint is ORDER — it lands before Phase 5 pooling. A leak found
  after labeling means relabeling ~300 judgments. The spike assertions are
  smoke tests, not that test.

## Open decisions
- D-P4-2 OPEN: naive vs normalized hybrid as the Day 25 pooling variant.
  09 schedules pooling (Day 25) before normalize.py (Day 32), so the pool's
  hybrid would be the BM25-dominated naive sum (03 §8). Decide at Day 23
  open. Prediction registered: naive-hybrid top-6 overlaps BM25-only top-6
  by >=4 of 6 on most queries.
- D-P6-1 OPEN: ranking ties. Before Day 34.
- D-P2-12 OPEN: LIST_STATE="all" admits 126 open PRs. Phase 4.
- D-P2-18, D-P2-22 OPEN: doc-revision batch. Now also 03 §5's pair-level
  mean wording (D-P3-3) and the superseded D-P2-24 latency figure.
- D-P3-2 OPEN: Neon pooled + create_pool() under Cloud Run churn. Phase 7.
- D-P5-2 OPEN: 01 §7 anchors / §8 subsystems. Day 25.
- D-P5-3 OPEN: 8497/8498 both confirmed in corpus. Before Day 25.

## Decisions log watermark
- Current through D-P6-1. D-P3-3 and D-P4-1 resolved this session;
  D-P4-2 opened.