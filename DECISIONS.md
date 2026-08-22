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

## D-P2-7 — AMENDED 2026-07-31: mechanism identified
Prior entry misattributed this. classify() DOES implement 07 §4's primary
bot rule, and the fixture DOES construct PRMeta — with six positional args
against a five-field declaration, so the committed test raises TypeError and
never reaches line 61. HANDOFF's sequencing note, _pr(), and classify() all
record six fields; only the dataclass disagrees. author_type was dropped from
the declaration after the Day-6 counter was printed and before the commit.
Fix: restore author_type: str in position 4. One line. Fixture unchanged.

## D-P2-7 — RESOLVED 2026-07-31: five defects in committed code, one cause
tests/test_corpus_filter.py had never executed. Four separate defects each
blocked it independently: `from collections import counter` (line 1),
missing pythonpath in pyproject.toml, `lambda p: created_at` in
group_duplicates, and `keep.number` for `keeper.number` in
apply_corpus_filter. A fifth — author_type deleted from the PRMeta
declaration while classify() and the fixture both still used it — is the one
that surfaced first, via an unrelated TypeError in github_client.py.
Root cause is single: the Day-6 session edited the file after its last green
run and committed without re-running. 11 §1's "end the session at the commit"
names exactly that window.
All five fixed. Suite green, Counter printed and READ, cache-read path
exercised with no network call.
Standing consequence: the golden assertion for a stage is not satisfied by
having been green once. It is satisfied by being green in the commit.

## D-P2-8 — CONFIRMED 2026-07-31: both caches namespaced by repo slug
.cache/diffs/ held bare-number FastAPI diffs from the Day-4 spike alongside
p5_-prefixed p5.js ones, and fetch_diff() wrote bare `<number>.diff`. No
collision existed yet — the FastAPI numbers on disk are 15xxx and p5.js is
at ~9k — but the namespace made one inevitable and a wrong cache hit does
not raise: it returns another repo's diff and the parser chunks it happily.
Silent data-shape bug, 11 §5's expensive category.
Fixed before any pipeline diff was fetched, so the cost was zero. The slug
is derived once in __init__ as self._slug and used by both helpers;
_cache_path renamed to _list_cache_path, since "the cache path" stops
meaning anything once there are two.
Consequence: the three 01 §7 anchor diffs (#8862, #8964, #8823) will
re-fetch through the new path. Three requests.

## D-P2-9 — CONFIRMED 2026-07-31: [bot] suffix stripped, not enumerated
01 §2 lists bot accounts unsuffixed (`dependabot`, `github-actions`);
GitHub sends them as `dependabot[bot]`. Exact membership therefore never
matched, and the rule only appeared to work because author_type == 'Bot'
fires one line earlier — the redundancy 07 §4 explicitly requires to be
independently testable.
Two options: add suffixed literals to BOT_ACCOUNTS, or normalize the login
before the lookup. Chose normalize — enumerating both forms doubles the set
and a new bot account still needs two entries. BOT_LOGIN_SUFFIX lives in
constants.py per 06 §6.
Test asserts the rule with author_type='User', so it cannot pass by way of
the primary rule.

## D-P2-10 — CONFIRMED 2026-07-31: ghost author guarded on both null shapes
GitHub sends "user": null for deleted accounts; `item.get("user") or {}`
already handled that. It has never been observed sending
{"login": null} — this is defensive, not a bug reproduced from a payload.
Kept anyway: .get(key, default) fires on a MISSING key only, so a
present-but-null login returns None and surfaces as an AttributeError on
.lower() inside classify(), three modules from the cause. `or GHOST_AUTHOR`
costs nothing and collapses both shapes.
Stated honestly in interviews as defensive coding, not as an observed bug.
Measured fact behind it: page 1 of processing/p5.js has ZERO null-user items
and author_type is uniformly 'User', so the ghost branch has never executed
in this project. Its only coverage is derived in-test.

### D-P2-12 — OPEN (2026-08-01)
LIST_STATE = "all" admits open PRs to the corpus. Legal: 02 §4's CHECK
permits outcome = 'open' and 01 §2 has no state rule. But it was inherited
from a constant, not chosen — and 03 §6's reason templates have no branch
for an open candidate, while invariant 17's outcome language assumes merged
or closed_unmerged. Resolve at Phase 4 when templates are written. Not
changing LIST_STATE now: a re-fetch under state=closed discards 44 cached
pages and the frozen snapshot 01 §15 depends on.

### D-P2-13 — CONFIRMED (2026-08-01)
The step-1 band (EXPECTED_TOTAL_LOW/HIGH) was pre-registered at 4,400-5,400,
failed against the measured 4,370, and was then rewritten to 4,300-4,450.
Recording the change of meaning explicitly: before the run it was a
prediction and could falsify; after it, it is a regression guard on
pagination and nothing more. The prediction it replaced is preserved in
JOURNAL.md, which is where 01 §14 says the record lives. Future bands
pre-registered for a first run get the same treatment — tightened after,
never silently.

### D-P2-14 — OPEN (2026-08-02)
Three of seventeen pull_requests columns (02 §4) do not fill from a /pulls list
item: files_changed, additions, deletions. All three carry DB defaults ('{}', 0, 0),
so a bad insert raises nothing and looks correct. All three source from the parsed
diff at 04 §5 step 4 — free, no extra request.

The fork is one question, not three: do they describe EVERY file in the diff, or
only files surviving 03 §2's exclusions?

- files_changed drives the Jaccard file-overlap signal (03 §1) and is GIN-indexed.
  Under the "every file" reading, a PR touching p5.Renderer.js + CHANGELOG.md
  Jaccards against every changelog-touching PR in the corpus. That argues for
  surviving-files-only.
- additions/deletions counted over surviving files will NOT match GitHub's own
  numbers for any PR touching a .md. Defensible — arguably better, since they then
  describe indexed content — but it must be a decision, not a side effect of where
  the counter sits in the parse loop.

The two columns must agree with files_changed either way. A row where
files_changed lists 3 source files but additions counts a 400-line changelog is
incoherent and nothing would flag it.

RESOLVE: before step 4 is written (days 11-12). Whichever reading wins, the
README at Phase 9 states which, because "files changed" in a published table
would otherwise be read as GitHub's number.

### D-P2-15 — OPEN (2026-08-02)
The .cache/prs/ snapshot is not frozen. D-P2-6 refetches the short last page on
every warm run, so new upstream PRs enter the corpus silently: 4,370 -> 4,371
overnight (#9030, #9031), open 124 -> 125.

01 §15 designates the cache AS the frozen snapshot the harness reads. It cannot
drift once labeling starts (Phase 5) — a judgment made against a corpus of 4,371
and a metric computed against 4,400 are not the same experiment, and nothing
currently flags the difference.

Options: a --freeze flag pinning a max PR number; a snapshot manifest recording
total + last number + fetch date, asserted on every subsequent run; or accept
drift until Phase 5 and freeze there explicitly.

RESOLVE: before Phase 5 labeling begins. Not blocking today's filter run.

### D-P2-4 — RESOLVED (2026-08-02): drop the ratio branch
Measured over the full 4,371-PR list. 63 groups, 69 exclusions.
Branch tally: exact=59, ratio-only=10.

The decision predicted "the ratio is headroom, not the load-bearing rule."
Confirmed at 63 groups instead of 4 — and the headroom is negative.

Four merged PRs were wrongly excluded, all via the ratio branch, all verified
on GitHub:
- #2780/#2781/#2782 "parameter validation tests part 1/2/3" — parts of #2592,
  ratio 0.970. Different files, different commits. All three merged.
  Excluded #2780 and #2781.
- #4409/#4438 "[feat] Improving tests ... dom module - I/II" — ratio 0.992.
  Author's own words: "first PR towards #4392" / "second PR towards #4392".
  Branches feat-tests-dom-I and -II. Both merged. Excluded #4409.
- #4369/#4388 "[feat] Updated inline documentation of color/core module" —
  ratio 0.970. Different modules, 4 files vs 9, both address #4368,
  branches templating-modules-color and -core. Both merged. Excluded #4369.

The failure has an exact shape: SHORT TITLES DIFFERING BY ONE CHARACTER, WHERE
THAT CHARACTER CARRIES THE MEANING. SequenceMatcher scores 1/2/3 and I/II and
color/core at ~0.97 because 60 of 62 characters agree. Semantically they are
maximally different — the digit IS the content. No threshold fixes this:
raising it to 0.995 still admits I/II at 0.992, and by then the branch matches
almost nothing the exact branch missed.

The exact branch produced 59 exclusions with zero observed false positives.
Dropping the ratio branch costs 5 plausible true positives (p5.sound
update/updates, Revise/Revised, the "(main)" suffix, loadPixels()/loadPixels,
textTomodel/text to model). That trade is correct under 01 §2's own logic: a
wrongly-excluded PR is silently gone from the corpus and invisible in every
metric, while a missed duplicate is one extra near-identical candidate that
retrieval handles.

CHANGE: titles_match() returns normalized-exact only. TITLE_SIMILARITY_THRESHOLD
and the SequenceMatcher import are removed, not left dead.
01 §2's "near-identical title" stands unamended — normalized exact match
(lowercase, whitespace-collapsed, trailing punctuation stripped) is a valid
reading of it. No doc unlock required.

PREDICTED after the change: 8 groups dissolve entirely (every non-anchor member
in them matched on ratio), so 63 -> 55 groups, 69 -> 59 exclusions, in_corpus
3,666 -> 3,676, total exclusions 705 -> 695 (15.9%). Registered before re-running.

NOTED, NOT IMPLEMENTED: every member of all three false-positive groups was
MERGED. A genuine resubmission has exactly one merged member — the others are
force-push casualties. ">1 merged member in a group" is therefore a mechanical
proof the group is wrong, and a candidate guard if duplicates ever need
tightening again. Not added now: the exact branch needs no rescuing, and an
unevidenced extra rule is what 01 §2 warns against.

RESULT 2026-08-03. Registered prediction: 55 groups / 59 duplicate_resubmission
/ in_corpus 3,676 / 695 total exclusions, on 4,371 PRs.
Actual on 4,372 PRs: 56 / 60 / 3,676 / 696.
in_corpus hit exactly. The uniform +1 on the other three is one drifted PR
forming a new duplicate group — bot_author (625) and housekeeping (11) are
unchanged, so the drift is neither. Attribution inferred from the counters;
not yet confirmed against the group log. CONFIRM BEFORE THIS NUMBER SHIPS.
D-P2-4 CLOSED.
CORRECTION 2026-08-05. The RESULT above is wrong on all three predicted
figures; the drift disguised the third.

Measured with spikes/day12_grouping_diff.py, running production
group_duplicates() twice over the frozen 4,372 cache — once as shipped, once
with the 0.95 branch restored by monkeypatch:

  ratio restored : 63 groups, 132 members, 69 exclusions (exact=59 ratio=10)
  as shipped     : 56 groups, 116 members, 60 exclusions

The 10 ratio-only members: 6 in two-member pairs, 2 in [2780,2781,2782],
2 in [283,286,310]. Seven groups dissolved. The eighth lost its anchor (#283)
and re-formed as [286,310] — 286 and 310 match exactly. That re-formation is
the entire discrepancy against the registered prediction.

True post-drop figures on 4,371 PRs: 56 groups / 60 duplicate_resubmission /
in_corpus 3,675. Registered prediction was 55 / 59 / 3,676 — MISSED ON ALL
THREE, each by one. The drifted PR was an ordinary in-corpus PR, carrying
in_corpus 3,675 -> 3,676 and making a wrong prediction read as exact.

The Day-11 commit message states the prediction "matched exactly." It is in
history and stays there; this entry is the correction of record.

Attribution RESOLVED against evidence, no longer inferred from counters.

All ten ratio matches now verified on GitHub. Precision 3/10:
  CORRECT  2196/2197 (1 merged), 2792/2793 (0), 8089/8090 (0)
  WRONG    2780/2781/2782, 4409/4438, 4369/4388, 8497/8498, 283/286/310
Dropping the branch fixed 7 false positives and created 3 false negatives.
Per 02 §4's asymmetry that is the correct direction. D-P2-4 stands.

Note for Phase 6: with D-P2-16's guard applied, the ratio branch scores 10/10
on these cases. NOT a reason to reopen — the guard's effect on the 47 groups
it does not flag is unmeasured. Recorded as a tuning variant only.

Note against D-P2-15: the cache has now drifted twice (4,370 → 4,371 → 4,372)
and the second drift moved a measured number. Severity raised from "before
Phase 5" to next session.

### D-P2-5 — RESOLVED (2026-08-02): case-sensitive patterns stand
report_housekeeping_near_misses() over all 4,371 PRs printed ZERO near-misses.
No title in the corpus matches the three 01 §2 patterns under IGNORECASE while
failing as written. The deliberate (update|Update) alternation loses nothing.
01 §2 needs no amendment; the case-sensitive transcription is correct as locked.

housekeeping came in at 11 against a predicted 84. Case sensitivity is NOT the
explanation — the near-miss report rules it out. Either p5.js maintainers rarely
type those three exact strings, or bot-authored ones were absorbed first
(classify() checks bots before housekeeping, and 625 PRs went to bot_author).
The model of maintainer behaviour was wrong; the filter is not.

### D-P2-15 — OPEN (2026-08-02)
The .cache/prs/ snapshot is not frozen. D-P2-6 refetches the short last page on
every warm run, so upstream PRs enter the corpus silently: 4,370 -> 4,371
overnight (#9030, #9031 appeared between the Day-9 and Day-10 runs;
open 124 -> 125).

01 §15 designates the cache AS the frozen snapshot the harness reads. It cannot
drift once labeling starts — a judgment made against 4,371 PRs and a metric
computed against 4,400 are not the same experiment, and nothing flags the gap.
EXPECTED_TOTAL_HIGH = 4_500 absorbed the change without comment; a band wide
enough to hide daily growth will not catch the day something goes actually wrong.

Options: a --freeze flag pinning a max PR number; a snapshot manifest recording
total + last number + fetch date, asserted on every subsequent run; or accept
drift and freeze explicitly at Phase 5.

RESOLVE: before Phase 5 labeling begins.

### D-P2-16 — RESOLVED (2026-08-05): discard duplicate groups with 2+ merged members
01 §2 says "keep the merged one, else the highest PR number." That phrasing
presupposes at most one member is merged. When several are, pick_keeper has no
defined behaviour and silently discards merged work. This guard enforces the
precondition the locked rule already assumes; it is not a new clause.

Measured over the frozen 4,372 cache. Merged members per group: {0: 10,
1: 37, 2: 9}. No group has 3+ (both such groups dissolved with D-P2-4).
The guard discards 9 of 56 groups, removing 9 exclusions:
  [286,310] [1188,1191] [6835,6839] [6636,6637] [7583,7601]
  [8167,8168] [8956,8957] [7747,7748] [8494,8513]

Five inspected on GitHub, all false positives, two distinct causes:
  DUAL-BRANCH PORT — the same change landed on main and dev-2.0 during p5 2.0
  development. 8494(main/font-fix) / 8513(dev-2.0/webgl-fix) and
  7583(main/patch-8) / 7601(dev-2.0/patch-10) were both requested explicitly
  by davepagurek in-thread. 8497/8498 carries a literal "(main)" suffix.
  Identical title, both merged, days apart — by design.
  TITLES THE AUTHOR DID NOT CHOOSE — 6636/6637 are both "Update
  contributor_guidelines.md", GitHub's web-editor default, patch-1 vs patch-2,
  +2/-2 vs +57/-56, unrelated edits. 286/310 are "p5.sound update" off a
  long-lived p5SOUND branch.

Guard verdict matches ground truth on all 8 groups inspected across D-P2-4
and this decision.

Metadata-only: merged_at is in the list payload, so this runs at step 2 with
zero extra requests and leaves 04 §5's step-2-before-step-3 ordering intact.
Any content-based alternative would need diffs and cost ~5,000 requests.

Implementation: a separate named function between group_duplicates() and
pick_keeper(), with its own test and teeth check. NOT folded into either —
pick_keeper's docstring describes a different rule.

Note: on [7583,7601] pick_keeper currently takes max() and keeps the dev-2.0
PR, dropping the main-line one.

01 §2 needs an amendment sentence. Not a Phase-2 gate (01 §2's corpus rules
are already applied); batch it with the outstanding doc revisions.

PREDICTION for the post-implementation run, registered before writing code:
47 groups / 51 duplicate_resubmission / in_corpus 3,685.

### D-P2-15 — RESOLVED (2026-08-05): the list cache is frozen by manifest
Mechanism: [FILL FROM THE sed — the short-final-page rule in
_read_cached_page]. Page 44 holds 72 of 100 items, so every run re-fetched it
and picked up PRs opened since. Correct behaviour for an interrupted fetch,
wrong for a completed corpus.

Three drifts: 4,370 (Day 9) -> 4,371 (Day 10) -> 4,372 (Day 11). The second
moved a measured number AND disguised a wrong prediction as an exact hit
(see D-P2-4 CORRECTION). Cost: one session.

Fix: a manifest at .cache/prs/<slug>_MANIFEST.json. When present,
iter_list_pages serves the snapshot from disk via _iter_frozen_pages and
issues zero requests. The frozen path deliberately bypasses
_read_cached_page, so the staleness rule is routed around rather than
weakened — an interrupted fetch on an unfrozen cache still resumes correctly.

Guards, each watched failing: wrong total, missing page, stray page beyond
the manifest's count, --refresh against a freeze. All raise CacheFrozen.
--thaw is the only way to re-fetch and prints the old snapshot first.

Frozen 2026-08-05: 44 pages / 4,372 PRs / #16..#9032.

Not gitignored-away: .cache/ stays gitignored, but the manifest is the
provenance for every exclusion count in the README and gets copied into
eval/artifacts/ as corpus_snapshot.json at Phase 5 (01 §15).

### D-P2-15 — AMENDMENT, 2026-08-06 (Day 13)

Guard verified. All four failure modes watched failing, one at a time, four
distinct messages and four distinct raise sites:

| Break | Site | Message |
|---|---|---|
| manifest total edited to 4371 | 224 | frozen cache holds 4372 PRs; manifest says 4371 |
| page 44 removed | 211 | manifest expects page 44; missing <path> |
| stray page 45 created | 218 | manifest says 44 pages but <path> exists — written to after the freeze |
| --refresh | 246 | --refresh against a frozen cache. Thaw deliberately: … |

Check 4 initially did not fire. `--refresh` was defined on `GitHubClient.__init__`
and honoured at three sites (`_read_cached_page`, `iter_list_pages`,
`fetch_diff`), but `scripts/index_repo.py` read `sys.argv[1]` only and never
supplied it — so `self.refresh` was `False` for the life of every run and the
guard was unreachable in practice. The run completed, printed both golden
assertions, and reported `elapsed 0s`. Fixed with argparse, which also rejects
unknown flags loudly. Reference-location class, same as `_diff_cache_path`
(Day 9).

**The zero-request claim is now measured, not inferred.** `GitHubClient.requests_made`
increments per `_client.get` — per attempt, not per call, since a retry spends
quota identically and step 3's budget (04 §5) is counted in round trips. The
frozen branch asserts it is zero; a frozen run prints `requests 0`. This
replaces the handoff's "zero HTTP lines in the log" criterion, which was not
runnable: `index_repo.py` configures `basicConfig` with no `FileHandler`, so no
log of a frozen run existed to grep.

**Procedural rule the code cannot enforce.** `--thaw` followed by `freeze`
re-derives the manifest from whatever the cache currently holds, so the repair
always resolves a disagreement in the cache's favour. Had the cache drifted to
4,373, the same two commands would have blessed 4,373 and printed `FROZEN`,
indistinguishable on screen. `--thaw` prints the old totals for exactly this
reason. **Thaw, read the printed total, then freeze — never chain them outside
a teeth check.**

Note: today's teeth checks re-derived the manifest. `frozen_at` moved from
2026-08-05T10:57:32Z to 2026-08-06T07:17:49Z. Contents identical — 44 pages,
4,372 PRs, first #16, last #9032 — so the snapshot every measured number rests
on is unchanged, but the manifest file itself is not the one Day 12 wrote.

---

### D-P2-16 — AMENDMENT, 2026-08-06 (Day 13)

The nine flagged groups were verified in commit `a7b4835`, which touched
`DECISIONS.md` only and reused `e94e9ba`'s subject line verbatim. `git log
--oneline` therefore shows two identical entries: `e94e9ba` is the measurement,
`a7b4835` is the verification and the registered prediction. Recorded here
because the history can no longer distinguish them and the README owes these
figures.

Still unimplemented. Prediction stands: **47 groups / 51 exclusions /
in_corpus 3,685.**

---

### D-P2-17 — RESOLVED, 2026-08-06 (Day 13)
**Diff chunking lives at `app/retrieval/chunking.py`, not `ingest/diff_parser.py`.**

`04 §3`'s folder structure lists both — `app/retrieval/chunking.py` annotated
"diff → hunks", and `ingest/diff_parser.py` unannotated. `09 §3` schedules
`ingest/diff_parser.py` for days 11–12; `12 §1` names `app/retrieval/chunking.py`
as one of the seven ritual modules. They cannot both hold the same logic.

**Resolved on reachability, not style.** The deployed service must chunk the
*query* PR's diff at request time before it can embed it — that is `03 §2`
executing inside `/analyze`. `ingest/` is declared script-only in `04 §3`, so a
parser living there is unreachable from the service, and the alternative is two
copies of the highest-edge-case-density code in the project (07 §2) drifting
apart.

Import direction is legal: `scripts/index_repo.py` imports
`app.retrieval.chunking` for step 4. The only import prohibition on the books is
invariant 12 — `app/` never imports from `eval/` — and this does not touch it.

Consequences:
- Build `app/retrieval/chunking.py`; test at `tests/unit/test_chunking.py` (07 §5)
- `ingest/diff_parser.py` is deleted, not filled
- `09 §3`'s day-11–12 row is stale — doc-revision batch
- The Doc 12 ritual fires unambiguously when `chunking.py`'s golden assertion passes

### D-P2-16 — RESOLVED AND IMPLEMENTED.
 Prediction 47/51/3,685 met exactly on all three. Nine groups discarded, 18 PRs returned to corpus, 9 exclusions removed. Note the handoff's list of ten pairs was wrong: 8497/8498 never formed a group — the  (main) suffix breaks normalized exact match. It is a real dual-branch port sitting in corpus as two merged near-identical PRs, i.e. the first concrete instance of D-P5-3's hazard, and evidence that D-P2-16 catches the grouped ports only.

### D-P2-18 — OPEN. 
07 §4's duplicate-triple invariant is factually wrong. The doc states the #8947/#8946/#8945 triple "leaves exactly one PR in corpus, and it is the merged one." Measured: none of the three is merged. #8947 survives via pick_keeper's highest-number fallback, not the merged branch. The doc names this as the worked example of the merged rule and it doesn't exercise it. Amend 07 §4 in the doc-revision batch; find a real merged-branch example. Note tests/unit/test_corpus_filter.py's fixture reuses those three numbers with fabricated merge state — it does test the merged branch, but on invented data under real PR numbers, which is its own small trap.### D-P2-14 — RESOLVED, 2026-08-07 (Day 14)
**files_changed, additions, deletions all derive from parse_hunks() output.**

GitHub's PR list endpoint returns none of these fields. The alternative to
deriving them from the diff is ~3,685 requests against the per-PR endpoint —
a rate-limit window spent on descriptive metadata. Rejected.

Rule, unified:
- files_changed = sorted distinct file_path over the PR's hunks
- additions / deletions = sum over the PR's hunks

Reverses the recommendation carried since Day 9, which had files_changed
excluding non-source paths while additions/deletions matched GitHub across
all files. Two counting rules in one parser pass required a defensive
comment to not read as a bug; one rule needs none, and the DB check is
stronger — sum(chunks.additions) must equal pull_requests.additions.

CONSEQUENCE, must be documented in 02 §4 and the README: these totals will
NOT match GitHub's PR page on any PR touching an excluded file.
deleted_file.diff is the extreme case — four deleted files, four @@ blocks,
+0/-0 reported. (Such a PR is caught by step 4b's no_source_content and
never reaches retrieval, so the divergence is cosmetic, not a leak.)

Not implemented: files_changed is computed but nothing writes to the DB yet.
Blocked on steps 3-7.

Open clause: the D-P2-2 406 case has no diff to count and would land as
{}, 0, 0 — indistinguishable from an empty PR. Needs
exclusion_reason = 'diff_unavailable', distinct from 'no_source_content'.
See 04 §5 step 3b, still unwritten.

---

### D-P2-19 — RESOLVED, 2026-08-07 (Day 14)
**parse_hunks() is pure str -> list[Hunk]. No pr_id, no token fields.**

06 §5 shows `parse_hunks(diff: str, pr_id: int)`. Superseded on two grounds:

1. Reachability. Per D-P2-17, /analyze chunks the QUERY PR's diff at request
   time. That PR has no row in pull_requests, so no pr_id exists to pass;
   the service path would have to invent a sentinel.
2. Terminology. 06 §2 states a hunk becomes a chunk at persistence. A hunk
   carrying a foreign key collapses the distinction the doc protects.
   store_chunks() attaches pr_id and repo_id.

token_count and was_truncated are NOT on Hunk. They require the MiniLM
tokenizer (03 §3), which would drag sentence-transformers into the
highest-edge-case-density module in the project and make test_chunking.py
load a model. Stamped at pipeline step 5, Phase 3.

Consequence: 07 §4 files "was_truncated is True exactly when
token_count > 256" under Chunking. It belongs to the embedding stage.
Doc-revision batch.

---

### D-P2-20 — OPEN, 2026-08-07 (Day 14)
**03 §2's exclusion list omits .yml / .yaml / generic .json.**

Observed, not hypothesized: binary_file.diff chunks
docs/en/data/sponsors.yml and sponsors_badge.yml — content "silver:" and
"logins:", a sponsor list embedded as source. The p5.js equivalent is
.github/workflows/*.yml.

NOT widening the list on one fixture. 03 §2 is locked, and the evidence is
available cheaply after step 4 populates chunks:

    SELECT split_part(file_path, '.', -1) AS ext, count(*)
    FROM chunks GROUP BY 1 ORDER BY 2 DESC;

Widen with a number behind it or leave it and say why. Resolve after the
first full parse run.

test_chunking.py pins current behaviour: `assert not is_excluded("b.json")`.
That assertion fails the day the list widens, which is the point.

---

### D-P2-4 — teeth check CLOSED, 2026-08-07 (Day 14)
The Day-11 open loop was framed unsatisfiably, not left undone.

test_high_ratio_titles_do_not_group carries two in_corpus assertions.
pick_keeper() excludes exactly ONE member of a group, so under any break at
most one of them can fire. "Watch both fail" was never achievable.

Watched, with `return True` forced at the head of titles_match():
- line 84 (assert not titles_match) — failed, `assert not True`
- line 87 (verdicts[9101]) — failed with
  Verdict(number=9101, in_corpus=False, exclusion_reason='duplicate_resubmission')
- line 88 (verdicts[9102]) — PASSED with the regression fully live

Prediction registered before the run and met: 9102 survives via the
highest-number fallback (neither PR merged, so D-P2-16 does not fire).

The pair is sound jointly; line 88 is dead weight in this scenario. A
single `assert [v for v in verdicts if not v.in_corpus] == []` would be
observable in one run regardless of keeper choice. Declined today — noted,
not fixed.

GENERAL FORM, worth carrying: any per-member assertion about a selection
function has at most one live branch.

### D-P2-21 — Corpus-size cut for diff fetching
**Status:** RESOLVED — NO CUT
**Date:** 2026-08-08 (Day 15)

09 §6's Day-14 marker fired, prescribing 500 PRs instead of full history.
Two subset rules were considered: recent-N and stratified across `Area:*`.
Stratified is rejected on evidence (D-P2-22). The cut itself is rejected on
measurement — both gates cleared.

**Gate 1 — time.** 50-PR seeded random sample, cold cache, measured
1.57s mean per diff (median 1.52, slowest 3.10). INTER_REQUEST_DELAY_S =
0.75 is 48% of that, so the run is roughly half delay-bound. Projected
3,685 x 1.57s = 97 min. Actual full run sustained ~1.64s/request. Quota is
a non-issue: 0.75s spacing draws ~2,290 req/hr against a 5,000/hr limit.

**Gate 2 — storage.** parse_hunks() over the same 50 cached diffs: 8.3
chunks/PR mean, 3 median, 53 max. Projected 30,659 chunks at 3,685.
Embeddings 47 MB + content 46 MB = 93 MB against 02 §11's 250 MB target.
Headroom is real even allowing for indexes and pull_requests rows.

**Why cutting would have been wrong regardless.** A smaller corpus does NOT
lower Recall@3. 01 §9 pools from the corpus and 01 §11 scores against the
pooled relevant set, so a smaller corpus yields a smaller relevant set and
fewer competitors for the top 3 — the number would likely go UP. That is
the hazard, not the reassurance: the cut would have flattered the headline
figure while making the task easier, and nothing in the harness distinguishes
the two. The genuine costs are cluster density (01 §11 puts clusters at 2-5
PRs; a 1-in-7 sample leaves most queries with zero grade-2 candidates), a
smaller published claim (10 requires corpus size to ship with the number),
and cross-corpus incomparability (01 §15's frozen-snapshot rule).

**Superseded clause.** The earlier draft required non-subset PRs to carry a
distinct `exclusion_reason` = 'outside_diff_subset', to avoid asymmetric
signal coverage (hot invariants 2 and 3). Moot — no subset exists. Retained
here because the reasoning applies to any future corpus bounding.

---

### D-P2-22 — 01 §8's `Area:*` stratification claim is false
**Status:** OPEN (doc-revision batch, with D-P2-18)
**Date:** 2026-08-08 (Day 15)

01 §8's p5.js amendment asserts that `Area:*` labels "make the stratification
machine-readable rather than hand-assigned." Measured over the 3,685
in_corpus set from the frozen cache:

- 11 distinct `Area:*` labels
- 215 / 3,685 = 5.8% of in_corpus PRs carry any `Area:*` label
- mean 1.05 per labelled PR — effectively no multi-labelling

Mapping §8's seven named clusters:

| §8 cluster | Reality |
|---|---|
| Friendly Error System | `Friendly Errors` (23) — different prefix |
| p5.strands | `p5.strands` (1) — different prefix, ONE PR |
| WebGL shaders | `Area:WebGL` (121) |
| Vector/Math | `Area:Math` (11) |
| image and colour | `Area:Image` (12) + `Area:Color` (3) |
| framebuffer/renderer | no label exists |
| output | no label exists |

**Second, independent finding: the scheme is retired.** Last-seen dates —
Area:Events 2019-06, Area:IO 2019-07, Area:Utilities 2019-09, Area:WebGL
(the largest, 121) 2023-12. Only Area:Typography reaches 2026, at 12 PRs
across eleven years, which reads as incidental.

**Consequence beyond D-P2-21.** 01 §5 draws query PRs from the recent end,
so query PRs will carry no `Area:` label at all. 02 §6's
`eval_queries.subsystem` column cannot be populated from labels and needs
another source — path prefix under `src/`, or hand assignment as §8
originally assumed. Resolve with D-P5-2 before Day 25.

Same defect class as D-P2-18: a locked doc asserting a property the data
does not have.

---

### D-P2-20 — `.yml`/`.yaml`/`.json` on 03 §2's exclusion list
**Status:** RESOLVED — partial
**Date:** 2026-08-08 (Day 15)

Resolved with the extension histogram over 50 parsed diffs plus an
is_excluded() spot-check, rather than the planned post-step-4 SQL query.
Kept-file extensions across the sample: .js 119, .json 6, .html 6, .mjs 6,
.vert 4, .frag 3, .yml 2, .all-contributorsrc 2, .glsl 1.

**The spot-check, not the histogram, is the finding:**

    keep  translations/es.json      <- DEFECT
    keep  .github/workflows/ci.yml
    keep  test/unit/color.js
    EXCL  README.md / docs/guide.md / package-lock.json

**`translations/es.json` surviving is a specified behaviour that is not
happening.** 04 §5 step 4b exists precisely because a translation-only PR
is human-authored, carries no distinguishing label on processing/p5.js, and
is invisible to every metadata rule. The non-Area histogram shows 29
`Translation`-labelled PRs, and step 4b's job is the ones WITHOUT that label.
04 §5 states the consequence directly: file overlap scores translation PRs
against each other at Jaccard ~1.0 while BM25 matches near-identical titles —
two of three signals at ceiling on content that means nothing.

`.all-contributorsrc` is the same class: pure metadata churn, no code.

**Resolution:**
- ADD locale `.json` under `translations/` to 03 §2's exclusion list
- ADD `.all-contributorsrc`
- DEFER `.yml`/`.yaml` — 2 of ~149 kept files (~1%), and CI config carries
  some genuine signal. Revisit if the full-corpus distribution differs.

---

### D-P2-23 — Transport errors retried at the `_request` layer
**Status:** RESOLVED
**Date:** 2026-08-08 (Day 15)

The first warm-cache run died at ~2,450/3,685 with
httpx.RemoteProtocolError ("Server disconnected without sending a
response") after the Mac slept. `_request`'s retry loop handled only
403/429, so a dead socket — no status code to inspect — propagated past it
and killed the run.

Sleep was the trigger; the uncaught transport error is the defect. Over
3,685 requests a dropped connection is expected regardless of lid state.

Caught as `httpx.TransportError` (parent of RemoteProtocolError,
ConnectError, ReadTimeout, ConnectTimeout) inside `_request`, with the same
exponential backoff as 403/429. Placed there rather than in callers so
retry has one owner.

**Side effect on `requests_made`:** the counter increments before the
attempt, so a transport failure counts as a request even though it likely
spent no quota. This makes it an upper bound on quota consumed — the safe
direction, and consistent with the existing per-attempt framing.

**UNPROVEN.** The successful re-run logged errors=0, so the except branch
has never executed. Teeth not watched.

---

### D-P2-24 — Invariant 11's chunk-count premise is 3.1x low
**Status:** OPEN
**Date:** 2026-08-08 (Day 15)

Hot invariant 11 reads: "No ANN index on chunks.embedding in v1. Exact
search at ~10k chunks is milliseconds with perfect recall." Measured
projection is 30,659 chunks — 3.1x the stated premise.

The decision is probably still correct: exact cosine over 30k x 384-dim is
plausibly tens of milliseconds, and 04 §7's cold-start budget dwarfs it.
But the stated reasoning no longer describes the system, and a locked
decision whose premise moved 3x cannot be silently renumbered.

**Required, both:**
1. Amend invariant 11's figure to the measured one
2. MEASURE actual query latency in Phase 3 rather than re-asserting
   "milliseconds" against a second untested number

Resolve at Phase 3, day 17 (vector similarity query).

### D-P2-25 — RESOLVED (2026-08-12)
`scripts/` may import `app/`. The prohibited directions are `app/ -> ingest/`
and `app/ -> eval/` (04 §3, 06 §10) — both exist to stop deployed state from
reaching a published number, and a local script reading service code runs the
other way. `index_repo.py`'s docstring claimed "never app/", which was written
on Day 11 when the parser was still expected to live in `ingest/`; D-P2-17
moved chunking to `app/` and the docstring did not follow. Stale comment, not
a locked decision. Docstring corrected.

### D-P2-26 — RESOLVED (2026-08-12)
Chunks deferred to Phase 3; Phase 2's deliverable is `pull_requests` only.
`chunks.token_count` is `NOT NULL` (02 §5) and its only legal source is the
MiniLM tokenizer, which arrives at pipeline step 5 in Phase 3 (D-P2-19).
Writing 0 today would be a value the `was_truncated` invariant (07 §4:
true exactly when `token_count > 256`) is built on top of.
Consequence: Phase 3 re-parses the same cached diffs that Phase 2 parsed for
`files_changed`/`additions`/`deletions` (D-P2-14) and 4b's zero-hunk rule.
The re-parse is deliberate — it costs seconds against `.cache/` and keeps
each phase's write set clean.

### D-P2-27 — RESOLVED (2026-08-12)
`pull_requests.raw` stores the list item minus `base`, `head`, and `_links`,
plus a flattened `head_sha`.
Measured across all 4,372 items: full 73.5 MB, stripped 14.8 MB — 58.7 MB
saved, 80%. `base.repo` is the same object on every row and duplicates the
`repos` table record-for-record; `_links` is reconstructible from `number`
and `full_name`. 02 §4 defines `raw` as fields "kept for future use but never
filtered on", so nothing queryable is lost.
`head.sha` is kept deliberately: it is the only identifier of the commit state
a diff was fetched at, which 01 §15's frozen-snapshot claim depends on.
Storage: 91 MB chunks + 14.8 MB raw ≈ 106 MB against 02 §11's 250 MB.

### D-P2-20 — RESOLVED (2026-08-11)
Exclusions added to 03 §2's list: `test/unit/visual/screenshots/**`
(~360 file appearances, all `.json`, screenshot-harness fixtures),
`.all-contributorsrc` (133), `.map` (8), `.obj`/`.mtl`/`.stl` (22).
All fall under 03 §2's existing "generated or vendored paths" clause.
KEPT with reasons: `.yml` (219) — a CI-config change is a real change with
real precedent value, and boilerplate over-matching is a scoring problem that
03 §8's per-query normalization exists to handle; excluding on suspected
scoring behaviour before Phase 6 measures anything is guessing. Dotfiles
(`.gitignore`, `.eslintrc`, `.jshintrc`, etc., 80) — same argument, quarter
the volume, and they rarely appear alone.
**`TRANSLATION_PAYLOAD` investigated and found CORRECT.** The prior claim that
`is_excluded()` keeps `translations/es.json` was false: that path does not
exist in the corpus. The real layout is `translations/<locale>/translation.json`
across 13 locales, which 03 §2's pattern matches exactly. The defect was in a
hand-written probe string in `chunk_projection.py`, not in the predicate.
Probe list corrected to real corpus paths.
Untested by the fixture: `.map`, `.obj`, `.mtl`, `.stl` (30 appearances total).
Known gap, accepted for MVP.

### D-P2-24 — OPEN (updated 2026-08-12)
Invariant 11's ~10k premise remains low. Projection was 29,406 at 3,685
in-corpus PRs; the corpus is now 3,196, so ~25,500 — still ~2.5x.
Amend the figure AND measure real query latency at Phase 3.

### D-P3-3 — RESOLVED (2026-08-13)
Neon project region: ap-southeast-1 (Singapore) → aws-us-east-1 (N. Virginia).

04 §9 and 08 §1 both require Neon in a US region so the database sits near
Cloud Run rather than across an ocean; 08 §9's checklist line "Neon project
created in a US region" was marked complete on Day 1 without the region
being read back. Singapore was the fast choice from Lucknow and every step
since — local scripts, psql, the eval harness — is unaffected by it, which
is why eighteen days passed without the error surfacing. Only the deployed
service's latency is governed by this, and the service does not exist yet.

Neon fixes region at project creation; it cannot be changed in place.
Resolved by creating a new project and re-running `index_repo --target neon`
from the frozen cache — 0 GitHub requests, faster than pg_dump/pg_restore,
and it re-exercises the write path. Old project deleted after verification.

Verified: us-east-1 host, pgvector 0.8.0 (unchanged, D-P1-3 still holds),
6 tables, 4372/3196, six-row reason breakdown identical to local.

**Phase 7 consequence, recorded here so it is not re-decided by default:**
Cloud Run region is `us-east1`. 04 §9 permits us-central1, us-east1, and
us-west1; us-central1 is the common default and would put the service a
continent from the database. Pairing is aws-us-east-1 ⇒ us-east1.

Cost of this fix today: ~40 minutes and no rate-limit spend. Cost after the
chunks write: a dump/restore of ~25,500 rows carrying 384-dim vectors, or a
full re-embed. This was the last cheap moment.

### D-P3-1 — RESOLVED (2026-08-15)
Bulk vector insert: pgvector asyncpg codec over a manual `'[...]'::vector`
string cast.

Context: `chunks.embedding` is `VECTOR(384)`; asyncpg has no native handling.
Options were formatting each vector as a text literal with a `::vector` cast
(proven in the Day-3 spike, no new dependency) or `register_vector(conn)`.

Chose the codec. Binary wire format — ~1.5 KB per vector against ~4.6 KB for
text, ~3× on the largest write in the project, repeated on every re-index.
Secondarily it matches the JSONB codec already registered in `connect()`;
two mechanisms for one problem in one file reads as arbitrary.

Cost: one pinned dependency, and `register_vector` must run per connection.

Consequence to carry: the read path returns a pgvector `Vector`, not an
ndarray. `.to_numpy()` is required before numpy touches it — relevant at the
Day-17 similarity query.

### D-P2-24 — UPDATED (2026-08-15), still OPEN
Measured corpus is 41,899 chunks against `02 §5`'s ~10,000 premise. 4.2×,
not the ~2.5× recorded at Phase 2. Below the documented 100,000 HNSW
threshold, so invariant 11 stands for now. Closes at Day 17 with
`EXPLAIN ANALYZE` on the vector query — latency, not chunk count, is the
criterion.

### D-P2-18 / D-P2-22 — doc-revision batch, appended
- `02 §9` storage table: measured 133 MB, not the estimated ~50 MB.
- `02 §5` chunk-count premise: 41,899 measured.
- `02 §5` truncation rate: 23.3% corpus-wide.

### D-P2-24 — CLOSED (2026-08-17)
No ANN index on chunks.embedding (invariant 11) stands at 41,899 chunks.

Measured, local Docker, EXPLAIN ANALYZE on VECTOR_SIGNAL_SQL:
  newest query PR (3,195 candidates, 41,885 joined rows) — 48.3 ms
  mid-history PR  (1,600 candidates, 22,903 joined rows) — 29.8 ms
  Seq Scan on chunks ~10 ms in both; the remainder is <=> arithmetic
  in the HashAggregate, over join output rather than the full table.

Rationale REPLACED, not confirmed. 02 §5 argued "single-digit milliseconds
at ~10,000 chunks" — wrong on chunk count, wrong on time, and silent on the
per-query-chunk fan-out. The decision survives on a different basis: the
sequential scan is ~20% of execution time, so an ANN index would trade
perfect recall for a fraction of a third of the cost.

Caveat carried forward: 03 §5 runs the query once per query chunk. At the
measured 13.1 chunks/PR the worst case is ~630 ms of server-side vector work
per query PR, excluding request-time embedding on Cloud Run's x86 CPU.
Revisit if a Phase 7 measurement pushes end-to-end past ~2 s, or beyond
02 §5's documented 100,000-chunk HNSW threshold.

### D-P2-18 / D-P2-22 — doc-revision batch, appended
- 02 §5 no-ANN rationale: replace with the measured basis above.
- 03 §5 SQL: alias is vector_score (violates invariant 6) and carries a
  $1::vector cast made redundant by D-P3-1.

### D-P6-1 — OPEN (2026-08-17)
Exact score ties in the vector ranking. Day 17 produced three PRs at
+0.7237 and two at +0.6568 — duplicated chunk content across 2015 merge PRs
yields identical MAX values. Recall@3 and MRR both depend on rank order,
which is arbitrary inside a tie. Decide a deterministic tie-break before
weight tuning (Phase 6, Day 34).

D-P3-3 — mean-of-top-3 operates on query chunks, not (query, candidate) chunk pairs. (2026-08-20)
Context: 03 §5 specifies aggregation over all pairs. VECTOR_SIGNAL_SQL collapses candidate chunks with MAX in GROUP BY, so pair-level scores never reach Python.
Options: (a) mean-of-top-3 over the 14 per-query-chunk values; (b) a second SQL without GROUP BY returning pair-level rows, ~13× volume.
Decision: (a).
Reasoning: the weakness 03 §5 names — one coincidental hunk inflating a PR — produces one high query-chunk value, which averaging the top 3 still dilutes. (a) addresses the actual failure mode at zero query cost.
Trade-off: not literal compliance with 03 §5. MAX composes exactly across both levels; mean does not, so the flagged variant means something slightly different from the doc's wording.
Consequence: 03 §5 joins the doc-revision batch. If Day 34 shows mean beating MAX materially, (b) becomes worth measuring.

### D-P4-4 — OPEN (2026-08-21):
 Bulk and prose PRs distort exactly one signal each while carrying no semantic relation. #9032 (workflow YAML, 7 files) produced 0.9945 cosines on near-duplicate text; #9027 (docs(Vector):, 74 files, +944/−237, no labels) overlaps 1,835 of 3,196 in-corpus PRs — 57% of the corpus. Both passed step 4b legitimately: p5.js keeps JSDoc inside src/**/*.js, so a docs-only PR produces real source hunks and no label rule can see it (labels = {}). Two instances found by measurement, not design. Decide before Day 25 whether this is a corpus-filter exclusion or a documented limitation. Also supplies the disqualification rule for the pending cluster re-run: file count far above the corpus median, or a docs(/workflow-path prefix.

### D-P2-12 — still OPEN,
 evidence attached. #9027 has outcome = 'open'. 03 §10's reason templates and 05's --flag colour both branch on merged vs. closed-unmerged; an open PR is neither and has nothing to report about itself. 126 such candidates can reach the top 3. Hard requirement before Day 25 — an open PR in a pool is a judgment a labeler cannot make.

 ### D-P4-3 — RESOLVED (2026-08-21)

**Context.** 03 §4 step 4 says "take every PR with file overlap > 0
(capped at 100)" but does not specify a cap ORDERING. SQL cannot
`ORDER BY jaccard` because SQL does not compute the Jaccard.

**Options.**
1. Arbitrary SQL LIMIT with no ORDER BY — planner-dependent
2. Fetch all `&&` matches, score in Python, sort descending, cap at 100
3. Recency-ordered cap in SQL — cheap, no transfer waste

**Decision.** Option 2.

**Reasoning.** Options 1 and 3 can silently drop a PERFECT-overlap
candidate, which directly contradicts 03 §4's stated rationale for the
union: "a PR with perfect file overlap but weak embedding similarity must
be able to enter the ranking." A cap that can drop the best-overlapping
candidate defeats the reason the union exists. Option 1 is additionally
non-deterministic across runs — the same reproducibility hazard as the
open dict-insertion-order loop.

**Measured (20 most recent in-corpus PRs, temporal filter and
self-exclusion enforced).** Median 103 overlaps, max 1,835 (#9027, a
74-file docs sweep), 18x spread. Cap binds on 12 of 20. Worst-case
payload 247 kB; median ~103 rows is under 30 kB.

**Trade-off accepted.** We transfer rows we discard. The vector signal's
~920 ms fan-out dominates this by orders of magnitude.

**Revisit if.** Corpus exceeds ~20k PRs, or payload exceeds ~2 MB.

---

### D-P4-4 — OPEN (2026-08-21, extended 2026-08-22)

**Bulk and prose PRs distort exactly one signal each while carrying no
semantic relation. Three instances, one per signal, all found by
measurement rather than design.**

| PR | Shape | Signal distorted |
|---|---|---|
| #9032 | workflow YAML, 7 files | vector — 0.9945 cosines on near-duplicate text |
| #9027 | `docs(Vector):`, 74 files, +944/-237, labels={} | file overlap — 1,835 of 3,196 = 57% of corpus |
| #7930 | `chore: enable eslint rules`, only 2 files, 3,428-token body | BM25 — length normalization |

#7930 is NOT the bulk-file shape. Its length is entirely in the body.

**Why they passed step 4b legitimately.** p5.js keeps its reference docs
in JSDoc blocks INSIDE `src/**/*.js`, so a docs-only PR produces real
source hunks. #9027 carries no labels, so no label rule could see it
either. 07 §4 already asserts the inverse case (Documentation label +
substantive .js change stays in corpus); this is the same rule cutting
the other way.

**Decide before Day 25:** corpus-filter exclusion, or documented
limitation?

**Also supplies the disqualification rule for the pending
day18_aggregation cluster re-run:** file count far above the corpus
median, or a `docs(` / workflow-path prefix.

---

### D-P4-2 — RESOLVED (2026-08-22)

**Context.** 09 schedules pooling at Day 25 and normalize.py at Day 32,
so the "hybrid" variant feeding the Day 25 pool would be 03 §8's naive
unnormalized sum — the one the spec calls arithmetically meaningless,
where BM25's unbounded scale silently dominates a 0.2 weight.

**Why it cannot be deferred.** 01 §9 draws the pool from the top 6 of
each of four variants, and NOTHING outside the pool is ever judged. If
the hybrid variant is BM25-in-disguise, the pool comes from three
distinct signals, not four. Any PR that only a properly normalized hybrid
would surface never enters the pool, never gets a grade, and is counted
as irrelevant when Day 36 scores the holdout. That is a hole in the
ground truth, unrecoverable after labeling without redoing ~300
judgments.

**Decision.** Pull normalize.py forward from Day 32 to before Day 25.

**Reasoning — and this was decided BLIND.** At Day 23 open the agreed
plan was measure-then-decide: once BM25 existed, compute naive-hybrid
top-6 against BM25-only top-6 across several queries and count the
overlap. That was explicitly CONDITIONAL on BM25 finishing with time
left. It did not. Per the condition agreed in advance, the decision
falls to the default: a hole in the ground truth costs ~300 judgments,
a slipped module costs a day.

**Registered prediction, still unmeasured.** Naive-hybrid top-6 overlaps
BM25-only top-6 by >=4 of 6 on most queries. Worth measuring after
normalize.py lands, as a check on the reasoning rather than as an input
to it.

---

### D-P4-5 — OPEN (2026-08-21, confirmed worse 2026-08-22)

**Numeric tokenization. TWO problems with different fixes.**

**(a) Mixed alphanumeric.** `p5` -> `p5`, `p`, `5`. Every PR in this
corpus says p5 — titles, bodies, basenames (`p5.Vector.js`).
Fix: drop `\d+` from _SUBTOKEN.
  - `p5`: parts=['p'], len 1, guard suppresses -> only `p5` emitted ✅
  - `9030`: parts=[], len 0, guard suppresses -> `9030` survives ✅
  - Cost: `500ms` loses its `ms` sub-token. Marginal.

**(b) Dotted numerics.** `2.3.2` in a title becomes three separate whole
identifiers, and `2` is emitted TWICE, inflating its own term frequency.
NOT fixed by (a). Needs a minimum-length rule on bare numerics — a
threshold, therefore constants.py per "no magic numbers in logic." Must
sit above version components (1-2 digits) and below issue numbers
(4 digits).

**TRAP.** `Resolves #9030` produces the bare token `9030`. Two PRs
resolving the same issue is one of the most valuable signals BM25 can
have, and no embedding will ever catch it. Any rule stripping bare
numbers destroys it.

**CONFIRMED WORSE (2026-08-22).** `p5`, `p`, and `5` are THREE OF THE
THIRTEEN negative-IDF floored terms. The tokenizer does not merely add
noise — it TRIPLES the corpus's worst-behaved term, each copy drawing
1.765 IDF, each multiplied by query term frequency.

**DO NOT fix after Day 25.** Changing BM25 scores post-pooling means the
pool was drawn from a different system than the one evaluated. Decide
WITH the pooling variants.

---

### D-P4-6 — RESOLVED (2026-08-21)

**Context.** Vector and Jaccard enforce `created_at < query.created_at`
in SQL. BM25 has no SQL — BM25Okapi is an in-memory list of token lists,
and get_scores() returns a score for every document including ones
created after the query. The library knows nothing about dates.

**Options.**
- **A.** One index over the full corpus; filter results before the cut.
- **B.** Rebuild the index per query over eligible documents only.
- **C.** Precomputed snapshot indexes at intervals.

All three produce the SAME candidate set. They differ in what IDF sees.

**The subtlety.** IDF is a CORPUS statistic. Under A it is computed over
documents that post-date the query, so a term appearing in 3 PRs before
the query date and 200 after is scored as df=203 — under-weighted
because of documents that did not exist yet. That is leakage of a second
kind.

**The two leaks are not equally severe.**

| | Candidate-set leak (invariant 1) | IDF leak |
|---|---|---|
| What leaks | WHICH PRs can be returned | HOW legitimate PRs are weighted |
| Effect | A future PR can count as a correct answer — inflates the number directly | Legitimate candidates are mis-ordered |
| Recoverable | No — invalidates every published number | Bounded, measurable, disclosable |

**Decision.** A.

**Reasoning.** B is exactly correct on IDF but makes the harness compute
BM25 differently from the deployed service, violating invariant 13 — and
the distortion it corrects DOES NOT EXIST in production, where every
indexed PR predates an incoming one. The IDF leak is an artifact of
evaluating on a frozen historical corpus, not a property of the system.
Fixing it only in the harness makes the harness measure a system that was
never shipped; fixing it in both makes production pay hundreds of ms per
request, on a scale-to-zero instance, for a problem production does not
have. C rejected on 06 §9's memory budget.

**Bounded.** IDF is logarithmic, and the same distortion applies to every
candidate within a query, so it shifts magnitudes far more than it
reorders. Reordering requires two candidates matching on DIFFERENT terms
whose IDFs are distorted by different amounts — real, but second-order.

**Measured.** 20 most recent in-corpus PRs: max 0.59% of the corpus
post-dates any of them (19 of 3,196).

⚠️ **THAT IS A LOWER BOUND.** 01 §8 requires stratification across >=6
subsystems, so the Day 25 query set will be SELECTED for cluster
coverage, not taken off the top. A framebuffer PR from six months back
could be 9%.

🎯 **RE-RUN the contamination query against the Day 25 SELECTED query set
and publish THAT number, not this one. Reopen if it exceeds ~5%.**

---

### D-P2-12 — OPEN, evidence attached (2026-08-21, third instance 2026-08-22)

LIST_STATE="all" admits 126 open PRs. 03 §10's reason templates and 05's
--flag colour BOTH branch on merged vs closed-unmerged. **An open PR is
neither, and has nothing to report about itself** — while the outcome is
the highest-value signal the product produces.

**Three instances, and the pattern is not coincidence:** #9027 (open,
1,835 file overlaps, highest fan-out in the sample), #7930 (open, 3,428
tokens, longest document in the corpus). Open PRs are disproportionately
the ones that sprawled and stalled — which makes them disproportionately
the outliers in every signal.

**HARD REQUIREMENT before Day 25.** An open PR in a pool is a judgment a
labeler cannot make.