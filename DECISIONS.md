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
**Status:** OPEN (narrowed — default is NO CUT)
**Date:** 2026-08-08 (Day 15)

09 §6's Day-14 marker fired; prescribed remedy is 500 PRs. Two subset rules
were considered: recent-N and stratified across `Area:*`.

**Stratified-across-`Area:*` is REJECTED on evidence** — see D-P2-22.

**Default: no cut.** Rationale, stated precisely because the obvious version
is wrong:

  Cutting the corpus does NOT lower Recall@3. 01 §9 pools from the corpus
  and 01 §11 scores against the pooled relevant set, so a smaller corpus
  yields a smaller relevant set and fewer competitors for the top 3 — the
  number would likely go UP. That is the problem, not the reassurance: a
  cut would flatter the headline figure while making the task easier, and
  nothing in the harness would distinguish the two.

  The real costs of cutting are (a) cluster density — 01 §11 puts genuine
  clusters at 2-5 PRs, so a 1-in-7 sample leaves most queries with zero
  grade-2 candidates and an undefined recall; (b) the claim shrinks, and
  10 requires corpus size to ship alongside the number; (c) cutting later
  makes figures uncomparable across corpora, which 01 §15's frozen-snapshot
  rule exists to prevent.

**Gates that can still force a cut** — both measured, not assumed:
  1. Seconds-per-diff over a 50-PR timing run, extrapolated to 3,685. Cut
     if the projection exceeds ~2 hours unattended, or if 3,685 requests
     against the 5,000/hr limit leaves no retry headroom (11 §7: this
     project's I/O estimates run 4-7x low).
  2. Chunk count and DB size after ~500 PRs land; cut if the full-corpus
     projection breaches 02 §11's 250 MB target.

**Clause holding regardless of outcome:** if a subset is fetched, non-subset
PRs are marked `in_corpus = FALSE` with a DISTINCT `exclusion_reason`
(e.g. `outside_diff_subset`). Leaving them `in_corpus = TRUE` with no chunks
gives BM25 and file-overlap visibility the vector signal structurally lacks —
asymmetric coverage across the candidate set, violating hot invariants 2 and
3. A distinct reason also keeps 02 §4's audit and the README's 5 exclusion
counts clean: a budget cut is not a content exclusion.

Resolve after the 50-diff timing run.

