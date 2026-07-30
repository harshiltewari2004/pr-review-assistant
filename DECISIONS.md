> Convention: D-P<N>-<n> numbers by the phase the decision AFFECTS,
> not the phase it was made in. Entries are appended in the order made.
### D-P2-1 — CONFIRMED (2026-07-25)
Day-2 GitHub API spike (spikes/day2_github_api.py) is throwaway; its patterns
(pagination, X-RateLimit-* handling, backoff, .diff media type) migrate into
ingest/github_client.py in Phase 2, not the file itself. 7 parser fixtures
harvested to tests/fixtures/diffs/ (07_testing.md §5): 5 real from
fastapi/fastapi — simple_single_file #16054, multi_file #16050, huge_hunk
#16049, deleted_file #16016, binary_file #15947; 2 hand-built —
at_marker_in_content, rename_only — as neither appeared in 600 recent PRs, and
§5 permits synthetic fixtures because the parser test cares about diff shape,
not provenance.

### D-P2-2 — OPEN (2026-07-25)
Production github_client.py must handle GitHub's 406 on the .diff media type for
very large PRs (seen on #15519, #15392). Options: fall back to /pulls/{n}/files
(paginated per-file patches), or log-and-skip and record the exclusion. The
spike logs-and-skips (06 §8); the production choice is deferred to Phase 2.

### D-P1-2 — OPEN (2026-07-25)
Primary evaluation repo: FastAPI vs p5.js (processing/p5.js).
p5.js is JavaScript and I contribute to it — domain expertise raises
label quality, and it merges the "contributor" and "project" narratives.
FastAPI is Python and partially de-risked (clusters already eyeballed).
RESOLVED BY: Day 4 embedding spike on two known-similar PR pairs per repo.
  - Both reasonable → p5.js primary, FastAPI as cross-language evidence.
  - p5.js weaker → FastAPI primary, p5.js as measured secondary.


### D-P3-1 — OPEN (2026-07-26)
Vector marshalling for app/db.py: manual ::vector string cast vs the
pgvector Python package's asyncpg codec. The day-3 spike used the manual
cast — zero new dependencies, verified round-trip on local and both Neon
endpoints. The codec is likely correct for Phase 3's bulk chunk insert
(06 §9 requires executemany or COPY; building 10k string literals is
wasteful). Decide when writing app/db.py, with a measurement.

### D-P3-2 — OPEN (2026-07-26)
Neon pooled endpoint + asyncpg prepared statements. Spike PASSED against
the pooled string with asyncpg's default statement cache, and also with
statement_cache_size=0. This was a single short-lived connection, NOT an
asyncpg pool, so it does not yet validate 04 §9's deployed configuration
(pooled string + connection pool + constant instance churn). Re-test with
create_pool() at Phase 7. Fallback is known if it fails.

### D-P1-3 — CONFIRMED (2026-07-26)
Local Docker pgvector is 0.8.5; Neon is 0.8.0. No v1 impact: 02 §5 locks
exact search with no ANN index, and the round-trip produced identical
results and an identical 9.359e-09 float4 delta on both. Relevant only to
02 §5's documented HNSW scale path, where version differences matter.
Neon's version is not user-selectable. Recorded, not actioned.

### D-P1-2 — CONFIRMED (2026-07-27)
Primary evaluation repo: processing/p5.js. FastAPI becomes cross-language
evidence, not the corpus.
Day-4 spike separation (similar MAX − control MAX), min across pair types:
fastapi +0.1882, p5js +0.3394 — both in 09 §5's ">0.15, signal
discriminates" band. Like-for-like by pair type split: zero-overlap
single-hunk favours p5js +0.1512, shared-file multi-hunk favours fastapi
-0.0730. Signs disagree, but both deltas are smaller than the within-repo
pair-type spread (fastapi 0.34, p5js 0.12), so at one pair per cell the
repo effect is not separable from the pair effect. That is 09 §5's
"comparable" branch → p5.js primary on domain expertise.
The embedding arm is a WASH, not a p5.js win. Do not state otherwise.
Consequence: 01 §2, §7, §8 and the corpus filter are FastAPI-specific and
must be rewritten before Phase 2 (see doc revision batch).

### D-P1-4 — CONFIRMED (2026-07-27)
Every similar pair gets a size-matched negative control; the recorded
result is the gap, not the raw cosine. Raw cosine is uninterpretable —
unrelated diffs share large surface vocabulary, and per-query min-max
(03 §8) discards absolute magnitude anyway, so only spread survives into
the ranking. Confirmed by the data: the p5js control scored 0.2236 and
the fastapi control 0.3094, both high enough that a bare similar-pair
cosine would have looked like a pass regardless of outcome.
Headline gap aggregates across pair types with MIN, not mean, locked
before the run: a strong zero-overlap pair must not mask a weak
shared-file pair.

### D-P5-1 — OPEN (2026-07-27)
Self-authored PRs in the p5.js corpus vs 01 §10's blind labeling
requirement. #8823 is mine and appears in the Day-4 pair set; the FES and
strands clusters contain more. Domain expertise is why p5.js was chosen
and is also what breaks the blind — I cannot fail to recognise my own
diff, and I know the intent behind it.
RESOLVED BY: a written rule before Phase 5 labeling begins. Candidates —
(a) exclude self-authored PRs from the 20-query set only, (b) exclude
them from candidate pools too, (c) keep them and report the count as a
stated limitation. (b) is cleanest and costs corpus density.

### D-P5-2 — OPEN (2026-07-27)
01 §7's grade-2 anchor #15515 ↔ #15613 was invalidated during Day-4 pair
verification, and §7's anchors are now FastAPI PRs for a corpus that is
no longer FastAPI (D-P1-2). Both grade-2 anchors, both grade-1 anchors,
and the grade-0 anchor need rewriting against p5.js.
The FES cluster (#8823, #8829, #8833, #8933) and the strands cluster are
the candidate source. #8829 ↔ #8933 is already verified as a superseded
attempt at the same change — 01 §6 rule 4, the highest-value case in the
system — which makes it a strong grade-2 anchor.
RESOLVED BY: the doc revision pass, before Phase 2.

### D-P5-1 — CONFIRMED (2026-07-28)
Self-authored p5.js PRs remain in the corpus and are eligible as both
queries and candidates. §10's blind requirement targets anchoring on
system rank; shuffling still delivers that. Authorship is a familiarity
bias, a different mechanism, and one that is measurable rather than
preventable: judgments.jsonl records a `self_authored` flag per pair,
the rate is published alongside the metric, and §12's re-test computes
kappa on that subset separately. If the subset kappa diverges materially
from the rest, the bias is reported as a measured limitation
(00_problem_statement.md §8), not discovered by a reader.
Unblocks 01 §7 anchor selection — #8823 stays eligible.

### D-P1-2 — RESOLVED (2026-07-27, reconciled 2026-07-28)
p5.js primary, FastAPI cross-language evidence and cached-not-indexed.

spikes/day4_output.txt closes with "inconclusive, D-P1-2 stays OPEN".
That line is superseded. 09 §5 pre-registered two branches — comparable,
or p5.js materially lower. Headline gaps were fastapi +0.1882 / p5js
+0.3394; p5.js is higher, so the branch taken is "comparable → p5.js
primary". The script's per-pair-type breakdown (pair A favours p5.js
+0.1512, pair B favours FastAPI -0.0730) is real and is why the decision
is stated as "the embedding arm is a wash, not a p5.js win" — but a wash
is comparable, and the inconclusive band was added after seeing the data,
which 09 §5 exists to prevent. The decision rests on ground 3 of
01 §2's selection — labeler domain familiarity — exactly as §5 specified.

### D-P5-1 — CONFIRMED (2026-07-28)
Self-authored p5.js PRs stay in the corpus, eligible as queries and
candidates. 01 §10's blind requirement targets anchoring on system rank;
shuffling still delivers that, and authorship reveals no rank. What
authorship creates is familiarity bias — unremovable, of unpredictable
sign, and confined to a countable subset. Measured, not prevented:
judgments.self_authored flags the pairs, the rate is published, and 01 §12's
re-test is stratified so every flagged pair is re-judged and the subset
kappa is computed separately. Under ten flagged pairs → report the count,
publish no kappa. Requires the 02 §7 column and the 01 §12 edit.
Anchor eligibility was never gated on this — 01 §7 anchors are open
rubric examples, not blind judgments.

### D-P2-3 — CONFIRMED (2026-07-28)
Translation PRs are excluded by content, not by label or path alone.
p5.js has no lang-* equivalent; translations are human-authored PRs
against translations/{locale}/translation.json (i18next; verified against
the current tree — en/es/hi/ja/ko/zh present). Two edits: 03 §2 excludes
the locale payloads at chunk level (NOT translations/, which also holds
dev.js and index.js — real source), and 04 §5 gains step 4b marking any
PR with zero resulting hunks as in_corpus = FALSE,
exclusion_reason = 'no_source_content'. Chunk-level exclusion alone would
leave file overlap at ~1.0 and BM25 at ceiling across all translation PRs.
Costs no extra API requests.

### D-P2-4 — OPEN (2026-07-29)
"Near-identical title" in 01 §2 is not operational. Implemented as: normalized
(lowercase, collapsed whitespace, trailing punctuation stripped) exact match,
OR difflib.SequenceMatcher ratio >= 0.95. The 7-day window is anchored to the
group's first member, not the previous one, bounding every group's span at 7
days and preventing transitive collapse across a month.

0.95 not 0.90: a false positive silently removes a real PR from the corpus,
and same-author-within-7-days already makes the conjunction tight. All four
observed p5.js cases have literally identical titles, so exact match alone
would have covered them; the ratio is headroom, not the load-bearing rule.

RESOLVE: after the first full list fetch, read the logged duplicate groups.
If any group contains PRs that are not the same change, lower the threshold
or drop the ratio branch entirely.

### D-P2-5 — OPEN (2026-07-29)
Housekeeping title patterns transcribed from 01 §2 case-sensitively, exactly
as written — including the deliberate (update|Update) alternation on the third,
which implies case matters and excludes "UPDATE". Widening to IGNORECASE would
change a locked rule on no evidence. Instead report_housekeeping_near_misses()
logs any title that matches only under IGNORECASE.

RESOLVE: read the near-miss log after the first full list fetch. If real
housekeeping PRs are slipping through on case alone, that is evidence, and
01 §2 gets amended rather than the code quietly widening.


## D-P2-2 — RESOLVED 2026-07-30: 406 on large diffs
Exclude, do not fall back to /pulls/{n}/files. Mark in_corpus = FALSE with
a fifth exclusion_reason literal, 'diff_unavailable', applied at 04 §5 step 3
(new location; step 2 is metadata, 4b is content).
Reasons, in order of weight: (1) a 400-hunk PR is a false-positive machine
under MAX aggregation — 03 §5's named weakness, already observed at Day 4;
(2) the /files payload is a second input shape into the highest
edge-case-density parser in the project (07 §2); (3) exclusion is reversible
per 02 §4, a bad parser path is not.
Obligations: count printed and read at ingest; count published in the README
at Phase 9; 406 only — 403/429 back off, other statuses log with their code.
The /files fallback remains a documented upgrade path.

## D-P2-6 — RESOLVED 2026-07-30: /pulls list query string
state=all, sort=created, direction=asc, per_page=100.
direction=asc is load-bearing: page numbers over GitHub's default descending
order are not a stable cache key, because PRs opened between an interrupted
run and its resume shift the pagination window and cause silent skips and
duplicates. Under asc, a full page is immutable; a short page is the tail
and is always re-fetched.
state=all rather than closed: 02 §4's CHECK admits outcome='open', and an
open PR predating the query is legitimate reviewer context. Excluding it
would be an unevidenced filter, which 01 §2 rejects on its own terms.

## D-P2-7 — OPEN 2026-07-30: PRMeta lacks author_type, but classify() reads it
corpus_filter.classify() line 61 implements 07 §4's PRIMARY bot rule
(author_type == 'Bot'). corpus_filter.PRMeta declares five fields and
author_type is not among them. Both are committed and passing.
That is only possible if tests/test_corpus_filter.py builds its 8-PR fixture
as something other than a PRMeta, so the Day-6 counter
{None:3, bot_author:2, duplicate_resubmission:2, housekeeping:1} was read
correctly and validated a shape the pipeline cannot produce.
Found by grepping the dataclass after a TypeError from from_list_item(), not
by a failing test.
Fix: add author_type to PRMeta; add it to from_list_item() (the TODO is
already in place); rebuild the fixture on real PRMeta objects; keep 07 §4's
two bot rules tested separately. Field-order change breaks positional
construction in the fixture — do it with that file open.
Due Day 8, BEFORE apply_corpus_filter() meets real client output.