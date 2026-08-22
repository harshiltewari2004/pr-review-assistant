# Handoff — 2026-08-22, Day 23 close (09 Day 22 COMPLETE — BM25 shipped in full)

## Done and committed
- abde1bf and predecessors (d7066bc, 17ef95d, 574f45d): BM25 complete
  (03 §7), all in app/retrieval/signals.py.
  - **tokenize()** — whole identifier AND sub-tokens. The
    `len(parts) > 1` guard is CORRECTNESS, not optimization: for a plain
    word, parts == [whole], and emitting both would double its own term
    frequency. Returns a list, not a set — BM25 weights by TF.
  - **build_document()** — title + body + BASENAMES of files_changed.
    Basenames not full paths: full paths would put src/core/webgl in
    nearly every document, which is directory structure rather than
    content, and path-level similarity is already 03 §6's job.
    `body or ""` — GitHub permits an empty PR description; None is
    ordinary, not an error. `rsplit("/", 1)[-1]`, not os.path.basename:
    GitHub paths are always forward-slash, and os.path.basename is
    platform-dependent.
  - **Bm25Index** — frozen dataclass: bm25 + parallel pr_ids +
    created_ats. rank-bm25 scores POSITIONALLY; nothing else recovers
    which score belongs to which PR. Frozen because rebuilding is a batch
    operation — a mutated index beside a stale parallel array is a silent
    wrong-answer bug.
  - **BM25_CORPUS_SQL** — no temporal filter, deliberate (D-P4-6).
    `ORDER BY p.id` is load-bearing, not cosmetic: positional scoring
    means an unordered fetch makes the harness irreproducible run to run.
  - **build_bm25_index()** — raises on empty corpus. BM25Okapi([]) does
    NOT error; it builds an index over nothing and returns empty arrays
    forever. On Cloud Run that is a service that starts green and
    retrieves nothing.
  - **bm25_signal()** — invariant 1 enforced in PYTHON, because BM25 has
    no SQL to put it in. FILTER BEFORE THE CUT. `strict=True` on the zip.
    `float(score)` at the boundary so numpy types do not propagate into
    normalization and eventually into pydantic. Sort key
    `(-score, pr_id)`, matching what scoring.py will use (D-P6-1).
  - **BM25_TOP_K = 50** in constants.py (03 §4 step 3).
- 6 golden assertions. Tests: **59 passing**.
- **TEETH-CHECK PASSED, prediction exact: 1 of 6 caught.** Break was
  cut-then-filter; returned 1 candidate where 3 were available. The five
  blind tests all used corpora smaller than their cut, so the cut was a
  no-op. The one that caught it was built so the INELIGIBLE documents
  scored HIGHEST — which required knowing BM25 favours short documents.
- **FALLBACK LADDER NEVER INVOKED.** Sub-token splitting shipped intact;
  07 §4's jsonable_encoder assertion passes.

## NEXT SESSION STARTS HERE — Day 24, HARD DEADLINE DAY
1. Gate: clean tree, `pytest tests/unit -q` = 59, `docker compose up -d`,
   `python -c "import os; print(len(os.environ['DATABASE_URL_DIRECT']))"`
   → 140. Use the python check, not `echo ${#VAR}` — `echo` passes on a
   shell variable whether or not it is exported, and a shell check
   reconstructing a code path is a different code path.
2. **ORDER IS FIXED. Do not reorder when tired:**
   a. **Temporal filter test (07 §9) — HARD DEADLINE, CUT NOTHING.**
      ⚠️ Day 23's 6 unit tests do NOT discharge this. They cover
      bm25_signal() in isolation; 07 §9 operates over the assembled
      candidate set across all three signals. **Read 07 §9 before
      assuming it is met.** Arriving at Day 25 believing a deadline was
      met is the failure mode.
   b. normalize.py (D-P4-2, pulled forward from Day 32). Type-by-hand.
   c. Union candidate set + naive weighted sum (09 Day 23, not started).
   If only (a) lands, the day succeeded. (c) can slide into Day 25-26
   without damage; (a) and (b) cannot.
3. **TEETH-CHECK OWED on tokenize().** Suggested break: remove the
   `len(parts) > 1` guard. Predict which of the 4 catch BEFORE running.
4. **build_bm25_index() has NO golden assertion.** Invariant 20 gap.
5. **Re-run day18_aggregation against a REAL cluster PR** (FES,
   p5.strands, WebGL, Vector/Math, image/colour, framebuffer, output).
   **D-P4-4 supplies the disqualification rule: file count far above the
   corpus median, or a `docs(` / workflow-path prefix.** Also owed
   against `neon` — everything so far is Docker/macOS.

## Measured — Day 22 (local)
- `&&` fan-out over 20 most recent in-corpus PRs, temporal filter and
  self-exclusion enforced: **median 103, max 1,835, 18x spread.**
  Cap at 100 binds on **12 of 20**.
- #9014 and #9002 both touch exactly 1 file: 103 vs 16 overlaps.
  **A 1-file PR's fan-out varies 6x by WHICH file.** That is 03 §6's
  documented bias, measured. README number.
- Worst-case payload (#9027, 1,835 rows): **247 kB**. Median ~103 rows is
  under 30 kB. Fetch-all confirmed cheap; the vector signal's ~920 ms
  fan-out dominates it by orders of magnitude.
- All in-corpus PRs have non-empty files_changed (count 0). Schema is
  NOT NULL DEFAULT '{}', so jaccard()'s empty guard still earns its place.
- idx_pr_files GIN index confirmed present — 02 §4's claim survived the
  migration, no reference-location gap.

## Measured — Day 23 (local)
- **avgdl = 146.2 tokens** over 3,196 docs. median 102, p90 303,
  max 3,428 (#7930), min 4 (#1148), **zero-token docs: 0** ✅
  Mean sits 43% above median — right skew. avgdl is NOT a typical
  document. With b=0.75, more than half the corpus gets a length BONUS
  and the top decile absorbs the penalty.
  **avgdl is DEFINED as MEAN document length — BM25's length correction
  is a sum-normalizing term, not a description of a typical document.
  This is the median/mean lesson appearing where MEAN is correct.**
- **BM25 index build: 7,558 ms for 3,196 docs, 40.9 MB tracemalloc peak.**
  Predicted 400-900 ms — **8-19x miss, worst gap of the session.**
- **rank-bm25 negative-IDF floor CONFIRMED FROM SOURCE, not memory.**
  `_calc_idf`: idf = log(N - df + 0.5) - log(df + 0.5); negatives are
  replaced by `epsilon * average_idf`, **NOT by zero**.
  Measured: average_idf 7.0609, epsilon 0.25 → **floor = 1.765**.
  A df=1 term scores 7.66, so **the floor is 23% of a maximally rare
  term** — handed to words BM25's own formula says carry no information.
  The floor is set by how rare the AVERAGE vocabulary term is (19,442
  terms, mostly rare), which is why it lands so high.
  **13 floored of 19,442: the to of and in is for a this js p5 p 5**
- **get_scores iterates the RAW query list** (`for q in query:`), and
  tokenize preserves repeats. **Query TF MULTIPLIES the score.** A query
  document saying p5 six times contributes 6 x 1.765 before length
  normalization enters. Confirmed from source.
- **`score > 0.0` guard drops only 3 of 3,196** on a real query (#9031).
  Nearly a no-op. Correct, free, provably lossless — but the top-50 cut
  does all the work, not the guard.
- Temporal contamination, 20 most recent in-corpus PRs: **max 0.59%**
  (19 of 3,196). Counts run exactly 0..19 — these ARE the 20 newest.

## Measured — Day 18 (carried forward, query #9032, local)
- 14 query chunks → 138 distinct candidates. Ceiling if disjoint: 700.
- Fan-out 920 ms / 14 chunks = 66 ms/chunk at VECTOR_TOP_K=50, localhost,
  EXCLUDING request-time embedding. **D-P2-24's ~630 ms worst case is
  superseded by ~920 ms.**
- chunk_hits: 53 of 138 (38%) seen in exactly one chunk's top 50; only 9
  seen in all 14. Cutoff bias, quantified.
- max vs mean_top_k: 8/10 top-10 overlap.
- Temporal filter: 0 leaks over the full 138-candidate union.
- ⚠️ **#9032 is a workflow-YAML PR. YAML is near-duplicate text and
  produced 0.9945 cosines. These numbers do not generalize and must not
  be quoted** until the cluster re-run lands.

## Prediction gaps
- **Day 22:** predicted `&&` fan-out 300-800 from a single query (#9032);
  got 44. Wrong SAMPLE, not a wrong model. The same property that made
  #9032's cosines unrepresentative made its fan-out unrepresentative in
  the OPPOSITE direction. **Fan-out is a property of the files touched,
  not of the corpus. One query PR cannot estimate per-query cost.**
  Then predicted median 150-400 / max >1,200; got 103 / 1,835.
- **Day 23:** doc length predicted mean ~200 / median ~150, got 146 / 102.
  Both ~30% high, from a 3-document sample that happened to contain a 432.
  **Third instance this week of small samples pulling the estimate toward
  whatever landed in them.**
- **Day 23:** build time predicted 400-900 ms, got 7,558 ms.

## Bug classes found — all invisible to tooling
- **A regex without a quantifier is legal Python and a valid pattern.**
  `_IDENTIFIER` shipped first without `+`, then without `_`.
  `ruff format` reformatted it; `ruff check` passed it. **Regex patterns
  are STRINGS — linter, formatter and type checker all treat them as
  opaque text. The only thing that inspects a regex is running it.**
  Caught in 4 seconds by printing output on 3 inputs (invariant 20).
- **`def build_bm_25_index` vs the spec's `build_bm25_index`.** Would
  have been SILENT had the call site been typed to match the definition —
  a legal function whose name disagrees with the spec and every other
  reference. Reference-location class. Mitigation on record:
  `grep -rn SYMBOL .` after moving any name.
- **The `score > 0.0` guard was discussed, agreed, and never reached the
  file.** 53 tests passed and 53 was CORRECT — no test existed that could
  see the difference. **Sibling of the reference-location class: the
  decision-never-landed class.** Caught only by an assertion encoding the
  intent.
- **`ruff check` is not `ruff format`.** Separate commands; the gate ran
  only the linter from Day 1. Both now.
- **`ORDER BY overlaps` is a syntax error** — OVERLAPS is a reserved SQL
  temporal operator. Avoid overlaps, end, user, order, limit as
  identifiers anywhere reaching SQL.

## Phase 7 consequence — biggest finding of Day 23
- Cold start is now: container start + MiniLM load (~360 MB) +
  **7.6 s BM25 build**. 04 §6's Action wakes with 12 retries x 10 s =
  120 s budget, so it will not TIME OUT — but a 10+ second first request
  on a PR-open event is the difference between a tool people leave
  installed and one they disable.
- **Strongest evidence yet for `--min-instances=1`** (open in Phase 7).
  ⚠️ Directly tensions with Always Free — a warm instance means non-zero
  idle billing against a $1 alert. Real decision, now with a number.
- Both figures are FLOORS. 7.6 s is macOS ARM, localhost, warm Postgres;
  Cloud Run is CPU-only x86 against Neon us-east-1. 40.9 MB is
  tracemalloc — Python allocations only, no numpy buffers.
- 03 §7 names the escape hatch itself: "the Postgres approach is the
  documented path if in-memory state becomes a constraint." A 7.6 s
  startup is arguably that constraint arriving. Phase 7, with evidence.

## 03 §7 IS MEASURABLY WRONG — doc revision required
- Spec: "At ~1,000 PRs this takes well under a second."
- Measured: 3,196 PRs → 7.6 s. Scaling linearly from the claim predicts
  ~3 s, so the corpus-size ratio does not explain the gap. Either
  BM25Okapi construction is superlinear in practice or the claim was
  never measured. **Push-back protocol: measured, does not hold,
  reopened.**

## Doc-revision batch
- **03 §7's "well under a second" build claim — measured 7.6 s.**
- **03 §7's numbered tokenization list is an OUTPUT description, not an
  execution order, and is impossible to follow literally.** Lowercasing
  at step 1 destroys the camelCase boundaries step 3 needs; treating `_`
  as non-alphanumeric at step 2 destroys the whole identifier step 4
  requires. Working order: extract preserving case and `_` → emit
  lowered whole → split while case is intact → emit lowered parts IF the
  split produced more than one.
- 03 §5's pair-level mean wording (D-P3-3).
- D-P2-24's superseded latency figure (~630 ms → ~920 ms).
- D-P2-18, D-P2-22.

## Interesting corpus cases — keep for the write-up
- **#1148**: title `Fixes #1145`, no body, 1 file → **4 tokens**, one of
  which is the issue number. At b=0.75 against avgdl=146 that document
  gets ~1.8x the score of an average-length one for the same single term
  match. Not a bug — length normalization doing its job — but a terse PR
  sharing an issue number can outrank a substantive one.
- **URLs are ~28% of #9032's tokens.** One GitHub permalink becomes 12
  tokens (`https github com processing p5 p 5 js issues 8674
  issuecomment 4586205003`). IDF kills their relevance contribution, but
  BM25 divides by |D|/avgdl — so **a PR that cross-references three
  issues is penalized on LENGTH for tokens carrying no information. The
  penalty tracks the author's linking habits, not the content.**
  `4586205003` appears in exactly one document: maximal IDF, zero
  matching power, pure length-divisor weight.
- **The p5.js PR template appears verbatim in bodies** (`pr checklist x
  npm run lint passes inline reference is included updated unit tests are
  included`). Same mechanism: a PR that kept the checklist is penalized
  on length relative to one that deleted it.

## Open loops
- **Ties (D-P6-1).** #8620/#8650 at +0.9445 (resubmission pair, benign).
  #7810/#7906 at +0.7899 — UNRELATED titles, identical to 4dp. Suspect a
  byte-identical shared chunk. Diagnostic: compare chunk bodies of tied
  PRs. If boilerplate chunks generate ties corpus-wide it is a chunking
  finding, not a tie-breaking one. **BM25 ties will be COMMON** —
  documents sharing exactly one rare term score identically.
- Deterministic rank ordering: when scoring.py sorts, key is
  `(-score, pr_id)`. bm25_signal() already uses this. Dict insertion
  order elsewhere still depends on which query chunk surfaced a candidate
  first — reproducibility hazard.
- `day17_vector_query.py` applies OFFSET 1600 to both ASC and DESC. The
  recorded "newest PR / 3,195 candidates" may not reproduce from it.
- `ON CONFLICT DO NOTHING` verification still unrun.
- 09 Day 15 `docker stats` container memory still owed. 512 MiB vs 1 GiB.
  **Now more urgent** — the BM25 index adds to MiniLM's footprint.
- Cloud Run is CPU-only x86. Never carry 39 chunks/s (MPS) or 5/s (Neon).
- test_embedding.py in tests/unit costs ~10 s. Move or accept.
- index_repo.py prints `no_source_content 470 predicted 220` every run.
- Local DB 147 MB vs Neon 133 MB — dead tuples. VACUUM FULL. Cite Neon.
- README owes: no_source_content 470 (12.8%), truncation 23.3% (02 §5),
  the 6x file-heat finding, avgdl 146.2 with its skew, and the BM25
  IDF-floor finding.
- Fixture misses .map/.obj/.mtl/.stl exclusions (30 appearances).
- `build_all_rows` reaches `gh._diff_cache_path`. Private-attribute debt.
- 12 Day-4 spike diffs still use the unreachable naming scheme.
- signals.py docstring typos, fix at the Doc 12 ritual: `chunk_hints` →
  `chunk_hits`, `mean_to_k` → `mean_top_k`, `query_created at` →
  `query_created_at`, `scorse` → `scores`. ruff never touches strings.

## Retired
- Day 17's "#4132 Test pr outranks real workflow PRs" is NOT a MAX
  weakness. It was an artifact of the spike printing one chunk's ranking.
  Aggregated over 14 chunks it sits at rank 29/138 (0.7083, hits 10)
  while the top five all have hits 14/14. Use the CORRECTED version in
  the Phase 6 write-up: the apparent weakness was a measurement artifact,
  found by aggregating properly.

## Open decisions
- **D-P4-6 RESOLVED (2026-08-21): BM25 temporal filtering = Approach A.**
  One index over the full frozen corpus; temporal filter applied to
  RESULTS, before the top-50 cut. Rejected B (rebuild per query): exactly
  correct on IDF, but it makes the harness compute BM25 differently from
  the deployed service (invariant 13) — and the distortion it corrects
  DOES NOT EXIST in production, where every indexed PR predates an
  incoming one. Rejected C (snapshots) on 06 §9's memory budget.
  **Trade-off:** IDF and avgdl are computed over documents that post-date
  the query, in OFFLINE EVALUATION ONLY. Bounded — IDF is logarithmic and
  the same distortion applies to every candidate within a query, so it
  shifts magnitudes far more than it reorders. Measured max 0.59%.
  ⚠️ **THAT IS A LOWER BOUND.** 01 §8 stratification will draw queries
  from further back; a framebuffer PR from six months ago could be 9%.
  🎯 **RE-RUN the contamination query against the Day 25 SELECTED query
  set and publish THAT number. Reopen if it exceeds ~5%.**
- **D-P4-5 OPEN — CONFIRMED WORSE THAN REGISTERED.** Two problems:
  **(a)** `p5` → p5, p, 5. Fix: drop `\d+` from _SUBTOKEN. For `p5`,
  parts=['p'], len 1, guard suppresses → only `p5`. For `9030`, parts=[],
  len 0, guard suppresses → `9030` survives. Cost: `500ms` loses `ms`.
  **(b)** Dotted numerics: `2.3.2` → three whole identifiers, `2` emitted
  TWICE. NOT fixed by (a). Needs a minimum-length rule on bare numerics —
  a threshold, so constants.py. Must sit above version components (1-2
  digits) and below issue numbers (4 digits).
  ⚠️ **TRAP: `Resolves #9030` produces the bare token `9030`. Two PRs
  resolving the same issue is one of the most valuable signals BM25 can
  have, and no embedding will catch it. Any rule stripping bare numbers
  destroys it.**
  **CONFIRMED: p5, p and 5 are THREE OF THE THIRTEEN floored terms.** The
  tokenizer TRIPLES the corpus's worst-behaved term, each copy drawing
  1.765 IDF, each multiplied by query TF.
  **DO NOT fix after Day 25** — changing BM25 scores post-pooling means
  the pool was drawn from a different system than the one evaluated.
- **D-P4-2 RESOLVED (2026-08-22): pull normalize.py forward.** Decided
  BLIND. Measure-then-decide was agreed at Day 23 open as CONDITIONAL on
  BM25 finishing with time left; it did not. A hole in the ground truth
  costs ~300 judgments; a slipped module costs a day. Prediction still
  unmeasured: naive-hybrid top-6 overlaps BM25-only top-6 by >=4 of 6.
  Worth measuring after normalize.py lands, as a check on the reasoning
  rather than an input to it.
- **D-P4-4 OPEN — THREE distortion mechanisms, one per signal:**
  #9032 near-duplicate YAML → vector (0.9945 cosines);
  #9027 74 files → file overlap (57% of corpus);
  #7930 3,428-token body but only 2 files → **BM25 length normalization.**
  #7930 is NOT the bulk-file shape; its length is entirely in the body.
  All three passed step 4b LEGITIMATELY: p5.js keeps JSDoc inside
  `src/**/*.js`, so a docs-only PR yields real source hunks and no label
  rule can see it (#9027 has labels={}). Three instances across three
  signals found by measurement, not design. Decide before Day 25.
- **D-P2-12 OPEN — THIRD instance. #9027 open, #7930 open, both
  outliers.** Not coincidence: open PRs are disproportionately the ones
  that sprawled and stalled, which makes them disproportionately the
  outliers in every signal. 03 §10's templates and 05's --flag colour
  both branch on merged vs closed-unmerged; an open PR is NEITHER and has
  nothing to report about itself. 126 such candidates can reach the top 3.
  **HARD REQUIREMENT before Day 25 — an open PR in a pool is a judgment a
  labeler cannot make.**
- **D-P4-3 RESOLVED (2026-08-21):** Jaccard cap ordering — fetch all `&&`
  matches, score in Python, sort descending, cap at 100. Rejected
  arbitrary SQL LIMIT (non-deterministic) and recency-ordered cap
  (systematic age bias). Both can silently drop a perfect-overlap
  candidate, contradicting 03 §4's stated reason for the union.
- **D-P4-1 RESOLVED (Day 21):** no Phase 4 scope cut.
- **D-P3-3 RESOLVED (Day 21):** mean-of-top-3 at query-chunk level.
- D-P6-1 OPEN: ranking ties. Before Day 34.
- D-P2-18, D-P2-22 OPEN: doc-revision batch.
- D-P3-2 OPEN: Neon pooled + create_pool() under Cloud Run churn. Phase 7.
- D-P5-2 OPEN: 01 §7 anchors / §8 subsystems. Day 25.
- D-P5-3 OPEN: 8497/8498 both confirmed in corpus. Before Day 25.

## Doc 12
- chunking.py COMPLETE (Day 14). No lag.
- **signals.py now has all three signals.** Ritual is owed at Phase 4
  close — which is now, once the union candidate set lands.
- Remaining: normalize.py, signals.py, scoring.py, reasons.py,
  eval/pool.py, eval/score.py.

## Fatigue
- Day 22: 2 one-token errors, session closed per 06 §13, resumed after a
  5-hour break.
- Day 23 evening: 4 one-token errors, all in linter-blind positions — an
  import list, two regex strings, a function name. **Comprehension was
  fine throughout**; the p5 fragmentation and the 03 §7 build-time gap
  were both diagnosed from output immediately. Typing degraded,
  understanding did not.

## Schedule
- **09 Days 1-22 COMPLETE. 23 calendar sessions used. One day behind.**
- Phases 1, 2, 3 closed. Phase 4 is 2 of 4 rows done (Day 21 Jaccard,
  Day 22 BM25).
- Owed next session: 09 Day 23 (union + naive weighted sum), 09 Day 24
  (temporal filter test), and normalize.py pulled forward from Day 32.
  **Two schedule rows plus a type-by-hand module in one session.**
- **Day 24's deadline is about SEQUENCE, not calendar.** The temporal
  filter test must land before Phase 5 pooling begins — a leak found
  after labeling means relabeling ~300 judgments. The union work can
  slide into Day 25-26 without damage. normalize.py cannot, per D-P4-2.

## Decisions log watermark
- Current through D-P6-1. This session: D-P4-2 and D-P4-6 resolved,
  D-P4-5 opened and confirmed worse, D-P4-4 extended to a third instance,
  D-P2-12 extended to a third instance.