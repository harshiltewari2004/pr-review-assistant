# Build Journal

## 2026-07-23 — Day 1

Ran `08_setup.md` §1–§5. Deployment (§6) deferred to day 2.

### Broke / fixed

- **`.env` is not auto-loaded, and an empty `$DATABASE_URL_DIRECT` fails
  silently.** `psql ""` falls back to the local Unix socket instead of
  erroring, so `001_init.sql` applied cleanly to local Postgres while never
  touching Neon — and the output looked like success. Fixed with
  `set -a; source .env; set +a` plus an explicit non-empty check before every
  psql call. Worth a guard in any future script that reads `DATABASE_URL*`.
- **Neon's pooled connection string contains `&channel_binding=require`.**
  Unquoted in `.env`, zsh backgrounds the line on `source` and the value is
  mangled. All `.env` values now single-quoted.
- **zsh treats `#` as a command, not a comment, when pasted interactively.**
  Cosmetic (`command not found: #`) but it garbles multi-line pastes.
- **`libpq` is keg-only.** `brew install libpq` succeeds but leaves no `psql`
  on PATH; needs a manual `/opt/homebrew/opt/libpq/bin` entry in `~/.zshrc`.
- **`git init` defaulted to `master`.** `06_code_standards.md` §3 assumes
  `main` and `08 §6` pushes `git push space main`. Renamed and set
  `init.defaultBranch` globally.
- **Seven dependencies shipped unpinned** in the first draft of
  `requirements.txt` — caught by `grep -c '=='` before the first push, not by
  anything automated. `06 §11` says pin everything; a manual check is the only
  thing enforcing it right now.
- **Rotated the Neon role password and `API_KEY`** after exposing both in a
  screenshot. Neon's role reset invalidates both connection strings at once,
  so recovery is cheap — but the screenshot habit is the actual risk and needs
  to stop.

### Surprised

- **torch 2.3.1 imports cleanly under numpy 2.4.6.** Expected the documented
  NumPy 1.x/2.x ABI break; it didn't fire. Recording it so the combination
  isn't re-litigated later. `sentence-transformers==3.0.1` also resolved
  `transformers 4.57.6`, far newer than the pin implies — imports fine, but
  day 4's embedding spike is the real test.
- **Neon free tier has limits the locked docs don't mention:** 100 CU-hours
  per month and 5 GB network transfer, both hard cutoffs that suspend compute
  rather than bill. `02_data_models.md` §9's 0.5 GB storage figure still
  holds. Storage budget is ~50 MB, so headroom is fine — but the CU-hour meter
  is worth a glance before a second full re-index.
- **pgvector on Neon is 0.8.0.** Local `pgvector/pgvector:pg16` version
  recorded for comparison; note any divergence here.

### Doc conflicts found

- **`corpus_snapshot.json`** — `01_evaluation_protocol.md` §15 lists it as a
  committed reproducibility artifact; `08_setup.md` §3 gitignores it.
  Resolved in favour of `01`: a gitignored snapshot means a clean clone can't
  reproduce the headline number, which is the whole point of §15. Removed from
  `.gitignore`.
- **No `.dockerignore` anywhere in the docs**, despite `08 §6`'s Dockerfile
  doing `COPY . .` — which would copy `.env` into a public HF Space image
  layer. Added one. Also excludes `eval/`, `tests/`, `ingest/`, and `scripts/`,
  reinforcing invariant 12 at the image boundary.
- **`requirements.txt` in `06 §11` lists five packages; the stack needs
  eleven.** Split into `requirements.txt` (runtime) and
  `requirements-dev.txt` (ruff, pytest, pytest-asyncio) so the deployed image
  doesn't carry test tooling.

### State at end of day

- §1–§5 complete. Six tables on local Postgres; Neon pending verification.
- `main` pushed to `github.com/harshiltewari2004/pr-review-assistant`.
- Deferred: §6 skeleton deploy (day 2), which frees nothing — day 2 already
  holds the GitHub API spike and the 7 fixture diffs.

### Locked decision invalidated — HF Spaces Docker now requires PRO

`04_architecture.md` §9 and `08_setup.md` §6 assume free Docker Spaces. As of
~July 2026 HF requires a paid plan (PRO, $9/mo) to create Gradio or Docker
Spaces; Static Spaces remain free. No changelog or docs update — surfaced only
as a "Paid" badge in the New Space form.

§6's real purpose was met locally anyway: image builds on python:3.11-slim
(torch in 143s), container binds 7860, /health returns. Image 1.6 GB.

**Decision: retarget to Google Cloud Run** (option C). Free tier is 180k
vCPU-seconds / 360k GiB-seconds / 2M requests per month, scale-to-zero, memory
configurable — the last point is what disqualifies Render, Koyeb, and Railway,
all capped at 512 MB against an estimated 700 MB–1.2 GB footprint with MiniLM
loaded. Requires a linked billing account even within Always Free; budget alert
set at $1.

Frontend splits off to a static host. `05_frontend.md` §5's seeded results were
already designed to render with zero network calls, so the recruiter path now
never touches compute at all — better than the HF design, not a concession.

Open risk, unmeasured: Cloud Run cold start with torch + MiniLM. Decides
whether --min-instances=1 (and therefore money) is needed. Measure in Phase 3
when embedding.py actually loads the model.

Also: added DATABASE_URL and API_KEY as HF *public Variables* rather than
Secrets. Rotated both. Second rotation today — the pattern is that credentials
keep landing somewhere that displays them.

CPU-only torch can't be pinned in requirements.txt: +cpu wheels are Linux/Windows only and macOS torch is already CPU-only. Moved to a separate Dockerfile RUN against the PyTorch CPU index, keeping requirements.txt portable. Also: building --platform linux/amd64 on Apple Silicon runs under emulation — minutes, not seconds.

## 2026-07-25 — Day 2
GitHub API spike done. Pagination + X-RateLimit-* handling + backoff all work;
quota behaved as expected (5000/hr). Auto-classifier harvested 5/7 fixtures from
real fastapi PRs; rename_only and at_marker_in_content didn't appear in 600
recent PRs — hand-built both (07 §5 permits it).
Two things not on the plan, both worth keeping:
- The .diff media type 406s on very large PRs (#15519, #15392). Spike logs-and-
  skips; Phase 2's client needs a real decision (D-P2-2). Good to know now.
- DECISIONS.md and HANDOFF.md were never tracked after day 1 (missed in the git
  add). Caught via git status at close. Now committed.


## 2026-07-26 — Day 3
pgvector spike passed on all four targets. Predicted all four cosines
correctly, including 2a → 1.0, which confirms <=> is magnitude-invariant
and makes 03 §3's stated reason for normalize_embeddings=True wrong. Keep
the flag, fix the reason.

Two process misses, both silent. The Neon gate check errored — I passed
the .env path as a connection string and psql read it as a database name,
so I never verified Neon was empty going in. And HANDOFF.MD was untracked
since day 2 despite the day-2 handoff claiming otherwise; the filename had
drifted from HANDOFF.md and macOS's case-insensitive filesystem hid it.
That is the second naming-drift bug in three days after delete_file vs
deleted_file. Both times: no error, wrong outcome, found by reading output
instead of trusting it.

## 2026-07-27 — Day 4
Vector signal discriminates on BOTH repos. Separation (min across pair
types): fastapi +0.1882, p5js +0.3394, both in 09 §5's top band. 03's
starting weights stand.

Prediction miss, and the useful kind. I predicted direction only — "p5.js
will win" — with no cosines and no threshold, which 01 §14 says cannot be
surprised. It wasn't. p5.js won pair type A (+0.1512) and LOST pair type B
(-0.0730), and both deltas are smaller than the within-repo spread across
pair types (fastapi 0.34). So the design can't separate repo from pair at
one pair per cell. D-P1-2 resolves to p5.js on domain expertise via 09 §5's
"comparable" branch, not on embedding quality. The embedding arm is a wash.
Next time write the six numbers, not the direction — I bet on the outcome
I wanted and got a result I can't call a win.

Two silent-ish catches. First run compared fastapi similar_b in the
source_only variant against p5js similar_b in default — my spec gap, not a
typo, and it made the B delta meaningless. The winning-hunk print is what
exposed it: p5.js's best match was two copies of the same test assertion.
Third instance now of "plausible output, no error" (after delete_file and
the .env-as-connstring). The countermeasure that has worked all three
times is printing the intermediate, not the result.

Truncation measured at 28% of hunks (9/32) on the production parse,
consistent across both languages — 27% fastapi, 29% p5js. 06 §12's worked
example used 18% illustratively; the real number is materially higher and
goes in the README per 02 §5. One hunk hit 3,698 tokens against a 256
limit. huge_hunk.diff's char-heuristic doubt is now closed.

Two transcription errors in the session — a semicolon for a colon in the
pair_score dict, and a dropped space in the winning-hunk f-string. Both
one-token, both caught. That's the 11 §4 fatigue bell, and the session was
already at its close.

## 2026-07-28 — Day 5, doc revision pass

- Wrote a verdict line into day4_embedding.py that was stricter than the
  criterion I'd fixed in advance. The script printed "inconclusive, D-P1-2
  stays OPEN" off a per-pair-type breakdown; 09 §5 pre-registered only two
  branches and the headline gaps (+0.1882 / +0.3394) land squarely in
  "comparable → p5.js primary". Caught a day later reading the output back,
  not at run time. Pre-registration only works if I also decide by the rule
  I wrote — post-hoc caution is still post-hoc. Reconciled in DECISIONS.md;
  the output file is a run record and stays as printed.

- Truncation across the day-4 spike: 9/32 hunks (28%), FastAPI 3/11, p5.js
  6/21. PREDICTION for the Phase 3 full index, not a corpus figure — n=32
  across ten size-matched PRs, one of which (#15937) was picked because it
  truncates. #15937's test file measured 3,698 tokens in one hunk, 14× the
  limit. Compare against the real rate at Day 19 and record the gap.

- The p5.js Similar-B full-diff winner was test/unit/webgl/p5.Shader.js on
  BOTH sides, opening with the identical test() string. MAX went 0.6788 →
  0.7074 on shared test scaffolding, not shared change semantics. That is
  03 §5's named MAX weakness showing up on real data at day 4, three phases
  before the aggregation question is due. First concrete argument for
  mean-of-top-3. Re-examine at Milestone A.

- My "p5.js handles translations through the contributor bot" claim was
  wrong, and my own evidence contradicted it — five "docs: add <user> as a
  contributor for translation" entries are the bot crediting a HUMAN whose
  PR is upstream and invisible to the bot rule. git ls-files confirmed
  translations/{en,es,hi,ja,ko,zh}/translation.json in the current tree.
  I had the disconfirming data on screen and drew the opposite conclusion.

- Chunk-level exclusion of locale JSON would have killed only the vector
  signal. File overlap would still fire at Jaccard ≈ 1.0 and BM25 on
  translation.json across every translation PR — two of three signals at
  ceiling on content that means nothing. Needed in_corpus = FALSE, which
  is 04 §5 step 4b. Nearly shipped the one-signal fix.

- Audit of the applied edits found 14 residuals, 4 of them contradictions
  between docs rather than typos — 01 §2 still claimed the corpus filter
  was metadata-only after 4b made it not, and 07 §4 still asserted that a
  docs+code PR gets excluded. A find-and-replace pass does not catch a
  claim that became false. Read the paragraphs around every edit, not the
  edit.

- Two of my own edits interacted: deleting the Documentation row left the
  paragraph above it pointing at a rule that no longer existed. Neither edit
  was wrong alone. Also missed 09 entirely on three passes because I'd only
  ever grepped it for the §5 gap bands. Audit the files, not the edit list.

- day5_doc_label_sample.py prints the count and leaves the verdict to the
  pre-registered rule in its docstring. Deliberate reversal of day4's
  pattern, made the same day I found the day4 bug. Scripts report numbers;
  criteria decide.

## 2026-07-29 — Day 6
Corpus filter. The surprise was that 01 §2 is not executable as written:
"near-identical title" and "within 7 days" both needed operationalizing, and
the 7-day window turned out to be genuinely ambiguous — pairwise-transitive
grouping would let a chain of similar titles collapse across a whole month.
Anchored the window to each group's first member. Logged both gaps as D-P2-4
and D-P2-5 rather than picking silently.

Second thing: built day 10's module before day 8-9's, which means the filter's
input shape was defined against GitHub's list payload rather than against real
code. Pinned it as PRMeta so github_client.py inherits the contract instead of
the reverse. 11 §10 is exactly about this and it nearly bit.

- Committed a spike with a message claiming the result was recorded, before
  running it. Third time the record has asserted something reality didn't
  back. The other two were caught by reading output and by git status; this
  one was caught by a commit message not matching what I said out loud.

  - .gitignore never had .cache/, despite 04 §5 specifying it. Invisible for
  five days because the directory didn't exist yet. Caught by reading a
  git status I'd only opened to ask a different question.

  2026-07-30 (Day 7) — client works, assertion green, D-P2-6 confirmed on real
data. Five one-token typos, two silent: `mereged_at` (every PR reads unmerged)
and `directions` (GitHub ignores the unknown param and serves descending order).
The bigger find came free from a TypeError: classify() reads pr.author_type and
PRMeta has no such field, so yesterday's passing fixture was built on a shape
the pipeline cannot produce. A prose contract in HANDOFF.md does not typecheck.
Stopped at the rule, several typos late.
## 2026-07-31 (Day 7 close) — 
five defects in code committed green on Day 6:
lowercase `counter`, missing pythonpath, `lambda p: created_at`, `keep` for
`keeper`, and author_type deleted from PRMeta while classify() and the fixture
both still used it. Four independently blocked import; the suite had never run
as committed. Found sideways, via a TypeError in unrelated new code. One cause:
edits landed after the last green run and before the commit — exactly the
window 11 §1 names. Also: pytest swallows print() without -s, so the Counter I
"read and verified" on Day 6 could not have been on screen. Adding pre-commit
and CI. Separately: nine one-token transcription errors across the session,
several of them silent (`mereged_at`, `directions=asc`). Pushed well past the
11 §4 bell and every defect after the second was found by a tired reader.
Silent naming drift, second occurrence: a field deleted from a dataclass after
its test passed and before the commit, same shape as delete_file/deleted_file
on Day 1. Nothing re-ran the suite between the two. Surfaced only because an
unrelated TypeError in new code sent me grepping the type.

2026-07-31 (Day 8) — tests only; the fetch never started. Three findings, all
about verification rather than code.
tests/fixtures/list_items.json was created holding the extraction SCRIPT
instead of its output. Fourth instance of one pattern: Day 2's uncommitted
ledger files, Day 6's spike output that read "command not found: python",
Day 7's test_corpus_filter.py that had never executed, and now this. Every
one existed, looked finished, and was wrong until something opened it.
Predicted one red before running pytest. Got zero — the `or GHOST_AUTHOR`
fix was already applied, so both null-path tests have only ever been green.
Teeth-check run afterwards to prove they can fail. A prediction against
stale code is not a prediction.
Measured: page 1 has zero null-user items and author_type is uniformly
'User'. The ghost branch has never executed in this project, so the comment
in from_list_item claiming the golden assertion catches it was describing
intent, not coverage.

## 2026-08-01 — Day 9

First full list fetch on processing/p5.js. Pre-registration per 01 §14.

| Prediction | Basis | Actual |
|---|---|---|
| ~4,900 PRs | 200 UI pages x 25 | **4,370 — miss, 12% high** |
| ~4,175 closed | 02 §9 | see Counter |
| ~49-50 pages | 100/page | 44 |
| first = #16 | cached page 1 | #16 — hit |
| ~1% of quota | ~50 of 5,000 | 44 req, 0.88% — hit |
| 12% exclusion, back-loaded | pre-2015 has no dependabot | not run |
| 4 Counter keys | 4b and step-3 reasons unreachable at step 2 | not run |
| dup grouping: seconds | ~1e5 SequenceMatcher calls | not run |

The UI-derived estimate lost to the doc. 02 §9's 4,175 came from the API;
my 4,900 came from multiplying a page count in GitHub's web UI. Counting
UI pagination is not a measurement.

Cache proven on real data: cold run 96s / 44 requests, warm run 3s /
1 request. Page 44 held 70 items so D-P2-6 never trusts it — it re-fetches
every time, by design. 04 §5's "a parser bug costs a re-parse, not a
re-fetch" now has a number behind it.

Number-space gap is expected: last PR is #9029 but only 4,370 exist.
GitHub shares one sequence between issues and PRs.

**Three symbol-rewiring misses in one day.** _diff_cache_path defined,
documented, never called. EXPECTED_* moved to ingest/constants.py while
scripts/index_repo.py kept local copies that shadowed them — the golden
assertion printed PASSED against a band I was not editing. Same shape as
Day 2's delete_file/deleted_file. Every one was "fix written, call site
not updated," and ruff caught none of the three: all three were legal
Python. New habit — `grep -rn SYMBOL .` after moving any name.

The teeth-check (11 §7) is what surfaced it. An assertion I had only
watched pass was indistinguishable from a comment.

 — processing/p5.js list fetch measured: 4,370 PRs across 44 pages,
#16 (2013-07-02) → #9029. States closed 4,246 / open 124. Outcomes merged 3,558
/ closed_unmerged 688 / open 124. Reconciles to 4,370 exactly. 02 §9 estimated
~4,175 closed; actual 4,246, within 1.7%. That figure is now measured, not inherited.

2026-08-02 — Prediction before the first apply_corpus_filter run (01 §14).
bot_author: 400              (weekly bot PRs since ~2018, 7.7 yrs x 52)
duplicate_resubmission: 36   (4 clusters/~600 observed -> 29 clusters at 4,370,
                              x1.25 exclusions per cluster since the keeper stays)
housekeeping: 84             (12/yr x 7 yrs of a human typing one of three exact
                              strings; bot rule runs first so bot-authored ones
                              never reach this branch)
Largest: bot_author, by roughly 5x over the next.
Total 520 vs the handoff's 12% ~= 524. Coincidence at this sample size, not
confirmation — the three individual numbers are the test.

2026-08-02 — Day 10. apply_corpus_filter over 4,371 real PRs. Counter printed
and read: {None: 3666, bot_author: 625, duplicate_resubmission: 69,
housekeeping: 11}. Predicted 400/36/84.

Two misses worth keeping. bot_author +56%: the weekly-since-2018 model was too
conservative on both rate and start year. duplicate_resubmission ~2x: the
CONVERSION was nearly right (predicted 1.25 exclusions per cluster, actual 1.10)
but the base rate was half what it should have been — I extrapolated from 4
clusters found in ~600 recent PRs and reasoned that force-pushing is a beginner
pattern so the recent rate would be inflated. Wrong: the groups run right across
the corpus, #283/#310 and #444/#445 are 2014. Reasoning about a base rate from a
non-random sample, then adjusting in the wrong direction on a plausible story.

The largest-category call was right, which is the part that mattered.

FIVE reference-location errors in one session, all the same class: the name was
right, the location was wrong. _diff_cache_path (carried from Day 9),
REASON_DIFF_UNAVAILABLE defined 60 lines BELOW the frozenset that reads it,
apply_corpus_filter never imported, the filter block pasted ABOVE the fetch that
produces its input, from_list_item looked for on PRMeta when it is a
module-level function in github_client.py. No typos, no logic errors — all
reference resolution. Day 9's habit (grep -rn SYMBOL after moving a name) proves
a name is referenced consistently; it says NOTHING about definition order.
Importing the module and printing is the check that covers that, and it caught
REASON_DIFF_UNAVAILABLE in five seconds.

KeyError: GITHUB_TOKEN again — third occurrence, first in a non-spike script.
Day 6 journalled it as "day5 spike was missing load_dotenv()", which is why it
did not generalise. The transferable version: ANY script reading .env needs
load_dotenv(), and an exported shell variable will silently paper over its
absence until a fresh terminal. Also: python-dotenv resolves relative to the
CALLING FILE, so load_dotenv() in a /tmp scratch script finds nothing and needs
an explicit path.

The .strip() fix to normalize_title changed no outcome — title.strip() already
ran first, so no real p5.js title reached the trailing-space branch. It was still
required: without it the exact-vs-ratio branch attribution would not have been
trustworthy, and that attribution is the entire evidence base for D-P2-4.

Teeth-check pattern that worked: the golden assertion was exercised from a
throwaway /tmp script rather than by editing scripts/index_repo.py and reverting.
Four breaks, four failures, zero risk of leaving one behind. Same for the
duplicate-evidence dump. Production files stayed untouched.

## 2026-08-03, Day 11
- Handoff was written from memory, not from the diff: it claimed two print lines
  were missing from index_repo.py that were already present. Cost a wasted step 0.
  Rule: write the handoff FROM `git diff`, with the diff open.
- Claude's revert-verification grep ("SequenceMatcher\|0.95" in ingest/) reported
  "revert incomplete" against comment and docstring text that is supposed to be
  there. Grep on prose cannot verify code state. The passing pinning test — which
  had just been watched failing — was the actual verification and was already green.
  Same reference-location failure class logged on Days 9 and 10.
- Prediction ritual paid: 4/4 numbers explained, and only because the fetch total
  was read first. The cache drifted a second time (4,371 → 4,372) and the drift
  landed inside a duplicate group. Without checking the total, this would have
  read as a prediction miss on three counters.
- Teeth check half-run. `assert` short-circuits; the two in_corpus assertions in
  test_high_ratio_titles_do_not_group have never been watched failing.
- Eight one-token slips, all dropped-space-after-punctuation, across four files
  including two inside a comment that ruff cannot reach. Threshold was hit early
  and the session ran on anyway. Fourth session with this pattern.

## 2026-08-05 Day 12
The Day-11 prediction (55/59/3,676) was recorded as "in_corpus hit exactly."
It didn't. True was 3,675. The cache had drifted by one PR overnight, and that
PR was in-corpus, so it carried the real number onto the predicted one.

Two errors cancelling are indistinguishable from correctness by inspection.
Nothing in the output looked wrong. It was recoverable only because three
things were written down in three places on three different days: the
pre-registered prediction, the drift, and the pre-drop branch tally
(exact=59 ratio-only=10) from the Aug-2 evidence run. Any one of them missing
and the wrong number ships to the README.

Second finding: group_duplicates() is greedy, so tightening titles_match()
released #283 and let #286/#310 re-form as a group. A stricter rule created
an exclusion. I predicted the change by subtraction; subtraction was the
wrong model.

Third, and the one I did not go looking for: verifying the nine PRs that
returned to the corpus surfaced a live defect in the rule that survived
D-P2-4. Exact title matching is deleting merged work right now — #286, and
eight more. p5.js ports fixes across main and dev-2.0 with identical titles,
and GitHub's web editor auto-titles PRs after the file. Neither is a
resubmission. Title matching cannot separate resubmission from continuation
at ANY strictness: the ratio branch broke on titles too similar to
distinguish, exact matching breaks on titles too vague to. The fix is not a
better predicate, it is a second signal — merged count (D-P2-16).

Verification was scheduled as an optional 10-minute spot check. It found the
larger bug. The pattern from Day 6 holds: artifacts look complete until
someone opens them.

Fourth: the run log lived in /tmp. It survived by luck. logs/ now exists.

Fifth: two FIND/REPLACE blocks I was given had non-unique anchors and both
mangled github_client.py — once splicing a class into another class's body,
once splicing a method signature into the next method's. Legal-looking edits,
caught only by ruff. Line-range replacement worked where string matching
failed twice. Not my transcription errors, but the same failure class:
reference location, not name.

## 2026-08-06 — Day 13

Opened by verifying state instead of trusting it, and the verification was the
useful part of the day.

**Claude's five session-open predictions: four wrong.** It predicted the tree
was still red from Day 12's syntax error, the freeze had never run, and no
manifest existed. All false — the repair, the freeze, and commit `9bf1d6f` had
all landed. Its stated cause: the handoff's line *"D-P2-15 code is written but
its teeth were never watched failing"* is precisely accurate, and it inflated
that into "the file doesn't parse" from memory of where the session ended.
Substituting a memory for a document, which is the same shape as the
reference-location errors already logged here. The one prediction that held —
total 4,372 — was the one that mattered: no fourth drift, and every Day-12
number stands.

**Fifth confirmed instance of "the artifact looks complete and is wrong until
you open it."** Teeth check 4 ran `--refresh` against a frozen cache and
*completed*: 44 pages, both golden assertions PASSED, full counter printed. No
raise, and no re-fetch either — the flag was discarded in silence. Worse than
either honest outcome, because a failing guard and a working guard both produce
visible evidence; this produced a clean-looking run. `elapsed 0s` against a
96-second cold fetch was the only tell, and I'd have skimmed past it.

**The same thing again, two hours later, and the grep caught it.** After
applying the request-counter blocks, the run printed no `requests` line. Two of
four `grep -n requests_made` hits — the client half applied, the observing half
not. Had I committed on the strength of `ruff` passing and `PASSED` printing,
the commit message would have claimed the frozen branch asserts zero requests,
and it wouldn't have. The grep-before-commit habit is now load-bearing, not
ceremonial.

**Dropped spaces in f-strings: seven more, all in already-committed code.**
`thefreeze`, `pages:{dupes}`, `#{n},predicted`, `{last}items-pagination`,
`{len(items)}PRs`, `items,got`, `page{page}:{len}items`. Day 11 logged 8 and
Day 9 logged 5 of the same class, though I haven't checked whether today's
overlap with those — Claude asserted a cumulative "nine across three sessions"
and that arithmetic doesn't hold either way. What's solid: **they cluster in
`assert` and `print` messages**, i.e. in code that only executes once something
else has already gone wrong, which is why none surfaced until read aloud. None
were typed today.

**One genuinely bad one:** `assert last < PER_PAGE, {f"..."}` — a set literal
where parens belonged. Legal, truthy, prints wrapped in braces, and one
keystroke from `assert (cond, "msg")`, the classic always-passes bug. In a
golden assertion.

**And a stale one:** the band-violation message named "the predicted band around
4900" — FastAPI's figure — while the constants it tests against hold p5.js's.
Corpus-switch cascade again. Fixed by interpolating `EXPECTED_TOTAL_LOW/HIGH`
into the message, so it reads from the same source as the assertion and cannot
go stale twice.

**Also found:** `a7b4835` reuses `e94e9ba`'s subject verbatim. Ledger-only
commits need their own subject line — `git log` can no longer tell the
measurement from the verification.

Numbers unchanged all day: 56 groups / 60 `duplicate_resubmission` /
in_corpus 3,676 at 4,372. Pre-guard. D-P2-16 next.

The guard hit 47/51/3,685 exactly, but the test protecting it was empty — three lists built, discard_multi_merged_groups never called. It passed, and would have passed forever, including after the guard was deleted. Two teeth checks in a row were silent sed no-ops that I read as passes because the pytest output looked plausible. Fixed by putting the grep before the pytest in the chain, so a failed substitution breaks the chain instead of producing a green tick. Sixth instance of the pattern this session: the output looked right and the process behind it was broken.

## 2026-08-07 — Day 14

app/retrieval/chunking.py written, 14 chunking tests, 28 passing. The
module took under an hour; the surrounding verification took the session,
and the verification is where everything was found.

**Fixture survey before writing tests — three findings.**
Printed block count, hunk count and every +++ path for all seven fixtures
before a single assertion existed. multi_file.diff turned out to be a
release PR: one source file, one hunk, plus .md release notes. Day 2's
auto-classifier bucketed on "more than one diff --git", which does not mean
what the filename claims. Renamed md_excluded.diff. huge_hunk.diff is the
actual multi-file fixture — 5 .py files, 23 hunks — and is the only thing
in the set that exercises hunk_index resetting per file.

Had I written test_chunking.py from the filenames, "multi-file parsing" and
"hunk_index reset" would both have been covered by a fixture that tests
neither, and the suite would have been green.

**Second finding: .yml is not on 03 §2's exclusion list.** binary_file.diff
embeds two sponsor YAML files as source. Logged D-P2-20 rather than
widening the list — the extension distribution query after step 4 answers
it with a number.

**All seven parse predictions met.** Registered before running: 1/1/1/0/0/2/23.
Actual: identical. Zero-hunk cases returned [] rather than raising.

**Claude error — the teeth check I designed did not have teeth.**
For the golden assertion's third line I proposed inverting
`assert not HEADER_NUMBERS.search(...)` to `assert HEADER_NUMBERS.search(...)`
and said watching it fail proves the regex is not a dead pattern. It proves
nothing of the sort: a regex with a typo produces the identical `assert None`.
The real check is matching the pattern against a raw header string directly.
Second time in two sessions that a verification step was itself the defect —
Day 13 was a test with no assertions, today was a teeth check that tested
the wrong direction. The class is: verification code gets less scrutiny than
the code it verifies.

**Day-11 loop closed as unsatisfiable, not undone.** See D-P2-4 addendum.
pick_keeper() excludes one member, so only one of the two in_corpus
assertions can ever fire.

**Risk marker: Day 14, "PRs and chunks in the database" — NOT MET.**
09 §6 names this checkpoint and prescribes the response. See HANDOFF.

## 2026-08-08 — Day 15

- Golden assertion line 3 closed. Ran the regex from HANDOFF and it matched,
  then realised that proved nothing: I had retyped the pattern, so a match
  only showed the string in the markdown file was live. Grepped it out of
  test_chunking.py:14 instead — byte-identical, so the assertion is genuinely
  live. The first attempt (inverting the assertion) and this second one were
  both invalid for the same underlying reason: neither touched the real
  pattern. Reference-location failure class, third occurrence.

- Predicted before running label_histogram.py:
    distinct Area:* labels    15-30        actual 11
    >=1 Area:* label          <15%         actual 5.8%
    union over seven areas    ~215         actual ~140 (est.)
    largest area              colour/image actual Area:WebGL (121)

- **The union prediction landed by coincidence and I nearly recorded it as a
  hit.** Derivation was 3685 x 0.10 x 0.70 / 1.2 = 215, and the actual total
  Area-labelled count is exactly 215. But the real fraction was 5.8% not 10%
  and the real overlap 1.05 not 1.2 — two errors cancelling. A prediction
  that lands through compensating errors validates a wrong model and is worse
  than a clean miss. Check the intermediate terms, not just the total.

- Prediction 4 was wrong because I answered from the recent end of the repo
  after explicitly warning about that skew one message earlier. Area:Color is
  3 PRs, third from the bottom.

- Two findings neither prediction was looking for: the `Area:*` taxonomy is
  ~1/3 the assumed size, and it was abandoned around 2023. Both fell out of
  the date-span column, which was added as a diagnostic for a recency floor
  inside each area — a feature that no longer has a use. Logged as D-P2-22.
  
- **Diff timing prediction — the decomposition is the lesson.** Predicted
  60 min for 3,685, actual projection 97. Looks like a 1.6x miss. It is not:
  0.75 of the 1.57s mean is INTER_REQUEST_DELAY_S, a constant I had just
  read off the page. My 60-min figure implied ~0.23s of latency+write;
  actual was 0.82s. **The part I actually estimated was 3.5x low** —
  squarely inside 11 §7's 4-7x band. The total only looked respectable
  because half of it was a constant. Do not log this as "1.6x low."

- 406 rate: 0/50 in the sample, 19/3,685 (0.5%) over the full run. The
  sample could not have distinguished 0.5% from 0% — rule-of-three upper
  bound on 0/50 is ~6%, i.e. up to ~220 PRs. Correct to have refused to
  publish a rate from it. **14 of the 19 sit above #7257, dense band
  #8090-#8449** — the p5.js 2.0 era, which is exactly where 01 §5 says
  query PRs come from.

- Warm-cache run died at ~2,450/3,685 when the Mac slept:
  httpx.RemoteProtocolError, no status code, straight past the 403/429
  retry loop. The sleep was the trigger; the uncaught transport error was
  the defect, and it would have fired eventually with the lid open. D-P2-23.
  Re-ran under `caffeinate -i`.

- **The crash output was misleading and I nearly chased a ghost.** It showed
  a last checkpoint at 150/3685, but the re-run reported 2,491 cache hits.
  Under `tee`, stdout is block-buffered; the process died without flushing,
  so ~2,300 checkpoints were written and never displayed. Reconciled by
  counting files: 3,666 = 3,685 - 19, plus 12 spike files = 3,678. **The
  file count was the ground truth, not the log.**

- ruff caught a live B905 in chunking.py — bare zip() over two re.split
  slices. Lengths are equal by construction today, but bare zip truncates
  SILENTLY, losing a hunk in the module whose job is not losing hunks.
  strict=True. It had been sitting in a committed, all-green tree, which
  means `ruff check` never ran before that commit.

- zsh globs `--include=*.py` before grep sees it. Quote glob-bearing flags.

## 2026-08-10 — Day 17
D-P2-20 prediction, registered before the exclusion change:
- chunks per PR mean: was 8.3, predict ___
- total at 3,685:     was 30,659, predict ___
- zero-hunk PRs in the 50-sample: was 2, predict ___


Four hypotheses about the corpus. Three withdrawn.

1. `is_excluded()` keeps `translations/es.json` — **false**, that path does not
   exist. Real layout is `translations/<locale>/translation.json`; 03 §2's
   pattern matches it. The probe string was invented, not sampled.
2. CRLF line endings corrupting `+++` paths — **false**, zero `\r` in the corpus.
3. Trailing tab surviving into `file_path` — **true that the tab exists** (361
   headers, all paths containing spaces, git's disambiguation terminator), but
   **false that it survives**: `_new_path` calls `.strip()` at capture.

Common cause, and the day's real artifact: **a shell reconstruction of a code
path is a different code path.** `awk`/`sed` pipelines don't call `.strip()`;
`parse_hunks` does. Every finding was an artifact of the instrument. To test a
predicate, run the predicate. Adjacent to the reference-location class — same
root, different surface.

The teeth check settled it with evidence rather than inference: breaking
`VISUAL_SCREENSHOTS` produced a failure message showing the screenshot path
with **no trailing tab**, through the real parser, on a real space-bearing
header.

`#7149`: 10 MB diff, 142,576-byte single chunk, `docs/data.json` — p5.js's
generated reference payload. Appears in exactly one PR. Legitimate blob, not a
parse defect. Handoff open loop closed. But it means the storage projection is
mean-driven with a heavy tail — median chunk 399 bytes, mean 1,554, and one PR
carried a fifth of the sampled content total.

Prediction (D-P2-20 chunk re-run): mean 8 — hit (8.0). Zero-hunk 3/50 — hit.
Total 30,660 — **miss**, actual 29,406. The two predictions were mutually
inconsistent: 8 x 3,685 = 29,480, not 30,660. The total was anchored on the
prior figure instead of derived from my own mean. Had the mean landed at 8.3
the total would have "confirmed" and taught nothing.

Seven one-token transcription errors, all in pasted-then-adjusted code:
`==[` spacing, `.diff` extension on a stem-taking loader, `exclusion`/`excluded`,
`Typing`, `md_only.dff`, a test function pasted into `chunking.py` instead of
the test file, and a docstring opener dropped mid-paste. That seam — paste,
then hand-edit — is where the type/paste split in 06 §13 gets blurry.

## 2026-08-12 — Day 18

**Phase 2's deliverable met.** `pull_requests` populated: 4,372 rows,
3,196 in corpus. First rows in the table since the schema was created on Day 1.

Prediction (zero-hunk PRs among 3,666 fetched diffs): **220 predicted, 470
actual** — 2.1x. It sits inside the 3/50 sample's 95% interval (roughly 48–620),
so the prediction wasn't broken so much as wrongly *shaped*: a 3-of-50 rate
should never have been extrapolated to a point estimate. A range was the honest
form. Registering "220" created false precision I then measured against.

The filter is right, not the projection. Fifteen random `no_source_content`
rows, zero false positives: translation payloads, `CODE_OF_CONDUCT.md`,
`steward_guidelines.md`, `.all-contributorsrc`, contributor additions, empty
merge commits, license scan reports. #8247 — "Improve Accessibility Guidance
for `describe()` Usage" — reads like a code PR from its title and is docs.
No step-2 metadata rule could have caught it. That is precisely what 04 §5
step 4b was written for.

Consequence: corpus 3,685 -> 3,196, a 13% reduction. Chunk projection drops to
~25,500. All five carried anchors verified still in corpus (#8862, #8964,
#8823 for 01 §7; #8497/#8498 for D-P5-3).

`raw` payload measured before storing rather than after: 73.5 MB full,
14.8 MB stripped. 80% of it was `base.repo` — the same object serialised 4,372
times, duplicating the `repos` row we write in the same transaction (D-P2-27).
Also: median item size (17,199) sits *above* the mean (16,811). Left-skewed —
the fixed metadata dominates and bodies are the minority of the payload. I
predicted the opposite.

`build_all_rows`'s signature changed from `gh` to `diff_path`; the call site
kept passing `gh`. Fourth reference-location instance this week. Ruff cannot
see it — `gh` is a valid in-scope name — and it only raised because
`GitHubClient` has no `__call__`. A callable would have run to completion
producing wrong paths.

Also this session: `ruff format` rewrote `index_repo.py` while the editor held
unsaved edits, producing a save conflict. Save before running the formatter.

## 2026-08-13 — Day 19

**Neon was in Singapore for eighteen days.** Surfaced only because the gate
command queried `$DATABASE_URL` and `$DATABASE_URL_DIRECT` and both returned
`repos.id = 4` — two databases cannot both hold id 4. `\conninfo` then showed
both pointing at the same Neon endpoint, pooled and direct, and no local
string in `.env` at all. The region was visible on the Neon dashboard from
day 1 and never read.

The class: a checklist item whose verification is ten seconds and whose
failure is invisible until a phase that is six weeks away. 08 §9 says "Neon
project created in a US region" — checking the box required looking at the
console, and the console was open at the time.

**`ingest/db.py` registered the jsonb codec with `decoder=json.dumps`.**
Encoder correct, which is why 4,372 rows wrote cleanly on two databases and
nothing raised. The decoder is the read path; asyncpg hands it raw text and
expects an object back, so every `SELECT raw` through `connect()` would have
returned a re-encoded string. Nothing reads `raw` yet, so it cost nothing —
it would have presented in Phase 5 as a data-shape mystery, not an error.

Fifth reference-location-class instance this month, and the first that is
symmetrical rather than misplaced: `encoder=`/`decoder=` are adjacent lines
with the same shape, and `json.dumps` on both reads as consistent. ruff
cannot see it; both are callables with compatible signatures.

**`LOCAL_DSN` was a hardcoded literal**, which is why `.env` had no local
variable and why the gate silently checked Neon twice. Now
`os.environ.get("DATABASE_URL_LOCAL", <compose default>)`, documented in
`.env.example` with the real value rather than a placeholder — it is
`postgres:dev` against a disposable container, and 07 §10 requires tests to
run against local Postgres, never Neon. Asymmetry kept deliberately: the
`neon` branch raises SystemExit on a missing variable, `local` falls back.
A wrong local target costs a re-run; a wrong remote target is a write to
the wrong database.

Both teeth checks watched: a wrong `DATABASE_URL_LOCAL` raised
`InvalidPasswordError`, proving the variable is read; `env -u` fell back and
wrote 4372/3196 to repo_id 2.

**Stale prediction constant:** the run still prints
`no_source_content 470 predicted 220`. The miss is recorded and closed; the
constant is now noise on every run. Update it to 470 or drop the line —
invariant 20 wants prediction constants set deliberately, and one that is
permanently wrong trains the eye to skip that line.

**Resident memory with MiniLM loaded: 360 MB peak RSS.** Predicted 600–800;
04 §9 estimated 700 MB–1.2 GB. Both high, mine by ~2x and the doc by ~3x.

The doc's estimate is not decorative — it is the entire basis for
disqualifying Render, Koyeb, and Railway at 512 MB. On this figure they were
not disqualified. The host decision stands anyway: this is macOS arm64, not
a linux/amd64 container, and it is peak across a load plus one four-word
encode rather than batch-32 over 256-token chunks. The container reading
(09 Day 15, `docker stats`) is the one that governs and is still owed.

If the container agrees, the Phase 7 consequence is a 512 MiB Cloud Run
allocation rather than 1 GiB — which doubles the request-seconds fitting
inside 04 §9's 360,000 GiB-second free tier.

Where the estimate came from is worth knowing: it predates the CPU-only
torch change, so it likely carried CUDA library weight the service never
loads.
## 2026-08-15 — Day 21

**Overwrote `ingest/pr_rows.py` with `chunk_rows.py` content.** Paste-target
slip; `PRRow`, `build_row`, `outcome_of`, `_ts`, `_lean_raw` gone from the
working tree. Recovered with `git checkout` because the file was committed at
Day-19 close. Uncommitted, it was unrecoverable. Not a fatigue signal —
five minutes into the session — but it is the whole argument for committing at
session boundaries rather than "when the feature is done."

**Chunk-count prediction missed 1.7×: predicted ~25,000, measured 41,899.**

Root cause is mine and it is a statistics error, not a data surprise. The
50-PR sample gave mean 22.0, median 7.5, max 198. I anchored the corpus
projection on the median because it resists outliers — correct instinct for
describing a typical PR, wrong for a total. A sum is always mean × count. On
right-skewed data the median systematically underestimates a sum, and the
skew here is severe. Corpus mean landed at 13.1 chunks/PR, between the early
slice's 22 and the projection's 8, exactly where a mean-based estimate would
have put it.

Rule: median for "what is typical," mean for "what is the total." Applies to
capacity, cost, and aggregate load generally.

`scripts/chunk_projection.py` undercounted ~60% (8/PR vs 13.1). Deleted — a
script emitting a number known to be wrong is worse than no script.

**`ORDER BY number` is a sampling decision, not a neutral one.** The 50-PR
run drew the oldest 50 of a 13-year repo: 22 chunks/PR against a corpus 13.1,
because early PRs carry initial structure and vendored files. Determinism read
as unbiased. It is not. Same trap in any "first N rows."

**My idempotency assertion was wrong; the code was right.** Predicted
`chunks written 0` on a re-run. Actual: resume skipped the done 50, `--limit`
sliced the *next* 50, 1,096 new chunks. `--limit` correctly applies after the
skip.

Consequence worth keeping: `ON CONFLICT DO NOTHING` was never exercised,
because the resume check stops the conflict from ever reaching Postgres.
Layered guards hide each other — the cheap outer check makes the inner
guarantee untestable through the normal path. Verified separately with a
self-referential INSERT ... SELECT expecting `INSERT 0 0`.

**Neon write ran at 5 chunks/s against local's 39 — 8× slower, 2h09m.**
Not Neon; it is ~250ms Lucknow→Virginia per round trip against a per-PR
commit. Direct consequence of the Day-19 region move, and the right trade:
indexing runs a handful of times unattended from a laptop outside the
production path; retrieval runs on every PR from Cloud Run us-east1, where
the same hop is sub-5ms. Do not carry 5/s into any Phase 7 estimate.

**Truncation, corpus-wide: 23.3%** (9,748 of 41,899). Supersedes the Day-4
spike's 28% on n=32. This is the README figure per `02 §5`.

**Determinism confirmed by accident.** Local and Neon were indexed in
separate runs and produced identical counts — 41,899 chunks, 23.3% truncated,
3,196 PRs. Same frozen cache → same hunks → same tokenization → same
truncation flags. Any order-dependence in `parse_hunks` or nondeterminism in
the tokenizer would have shown as drift.

**Storage: 133 MB Neon, 147 MB local, same rows.** The 14 MB gap is dead
tuples from repeated `UPSERT ... DO UPDATE` runs locally — MVCC leaves old row
versions until vacuum. Cite the Neon figure. `02 §9` estimated ~50 MB total;
actual is ~2.7× that, still 27% of the 0.5 GB quota. `02 §11`'s "under
250 MB after full index" passes. `02 §9` says re-measure after the first full
index — done, doc owes the update.

**D-P2-24 is worse than recorded.** `02 §5`'s no-ANN-index rationale assumes
~10,000 chunks; measured 41,899, so 4.2× not ~2.5×. Under the documented
100,000 HNSW threshold, so the decision likely holds — but "likely" is not an
answer. Day 17's `EXPLAIN ANALYZE` on the similarity query closes it with a
measurement.

## 2026-08-17 — Day 21 (Phase 3 Day 17)

The temporal filter passed vacuously on the first run. The spike picked the
newest in-corpus PR as the query, so nothing could postdate it:
"Rows Removed by Filter: 1", and that 1 was the query PR caught by id <> $4.
The predicate removed zero rows. A <= instead of <, or the clause deleted
outright, prints identical output. Re-ran against a PR 1,600 deep in history
— 1,596 rows removed, assertion still green, now meaning something.

Same shape as the Day 9 shadowed-constants defect: correct code, green
result, no evidence. Teeth-check applies to filters, not only to tests.

Second surprise: query cost tracks preceding history, not corpus size.
48.3 ms for the newest PR against 29.8 ms mid-history, because <=> runs over
join output rather than the full table. The temporal filter is a performance
feature. The newest PR — the actual production case — is the worst case.

Five one-token faults across the session (numpy as numpy, ndarry,
c.embeddings, c.repo, a 16-space indent) and ran past ruff errors twice.
All mechanical, none semantic, all caught in under a second by tooling.
Closed after the measurement rather than starting Day 18.

Also noted: three PRs tied at exactly +0.7237. Duplicate chunk content
across 2015 merge PRs. Logged D-P6-1.

Day 21 (2026-08-20). Teeth check on aggregate_chunk_scores: break 1 (scores[-1]) predicted 3 failures, got exactly 3 — and the predicted pass held, test_single_score_is_not_a_special_case cannot distinguish max from last with one element. Break 2 (/ MEAN_TOP_K) predicted 1 failure, got 2 — prediction missed; the single-element test fails there too. The two tests are blind to opposite defects. Also: first teeth run had both breaks live simultaneously; attribution only survived because the branches are disjoint. Revert between breaks.
Spike predictions: #4132 top-3 → miss, rank 29/138; union 150–250 → miss, 138; overlap max/mean 8/10; top result chunk_hits 14/14.
Correction to the record: Day 17's "#4132 outranks real PRs" was an artifact of printing one chunk's ranking, not a MAX weakness. Aggregation promoted 28 real matches past it.
Correction to D-P2-24: fan-out is 920 ms / 14 chunks at production VECTOR_TOP_K=50, not ~630 ms. Day 17's figure used the spike's display TOP_K=10.
Open: #7810 / #7906 tie at +0.7899 with unrelated titles — suspect a byte-identical shared chunk. Feeds D-P6-1.
Open: day17_vector_query.py applies OFFSET 1600 to both ASC and DESC, so the recorded "newest PR / 3,195 candidates" figure may not be reproducible from that script.

Predicted && fan-out 300–800 from #9032; got 44. Wrong sample, not a wrong model — #9032's workflow-YAML files are edited a few times a year. The same property that made its cosines unrepresentative made its fan-out unrepresentative, in the opposite direction. A single query PR cannot estimate per-query cost; fan-out is a property of the files touched.
Distribution over 20 recent queries: median 103, max 1,835, 18× spread. Cap at 100 binds on 12/20. #9014 and #9002 both touch exactly 1 file — 103 vs 16 overlaps. A single-file PR's fan-out varies 6× by which file it touches. That is 03 §6's documented bias, measured. README number.
ORDER BY overlaps is a syntax error — OVERLAPS is a reserved SQL temporal operator. Same class as the existing zsh: bare SQL is not a command loop. Avoid overlaps, end, user, order, limit as identifiers anywhere that reaches SQL.

## 2026-08-21 — Day 22. Jaccard.

- **ruff check is not ruff format.** They are separate commands and the
  commit gate has only ever run the linter. Caught when hand-typed
  `jaccard()` passed `ruff check` with no spaces around `:`, `,`, `=`,
  `->`, `&`, `|`. `len(set_a&set_b)/len(set_a|set_b)` — unspaced bitwise
  operators next to a division is exactly the shape where a misread
  produces a bug that reads fine. Full-tree format was a 3-file diff, so
  the tree was in better shape than the missing command suggested.
  Both commands in the gate from now on.

- **Predicted `&&` fan-out 300-800 from a single query (#9032); got 44.**
  Wrong SAMPLE, not a wrong model. #9032's workflow-YAML files are edited
  a few times a year. The same property that made its cosines
  unrepresentative (0.9945) made its fan-out unrepresentative in the
  OPPOSITE direction. **Fan-out is a property of the files touched, not
  of the corpus. One query PR cannot estimate per-query cost.**

- **Then predicted median 150-400 / max >1,200; got median 103 / max
  1,835.** Distribution more skewed than modelled at BOTH ends.
  Cap binds on 12 of 20.

- **#9014 and #9002 both touch exactly 1 file: 103 vs 16 overlaps.**
  A single-file PR's fan-out varies 6x by WHICH file it touches. That is
  03 §6's documented bias, measured. README number.

- **`ORDER BY overlaps` is a syntax error.** OVERLAPS is a reserved SQL
  temporal operator; Postgres accepts it as an alias with explicit AS but
  parses a bare one in ORDER BY as the operator. Avoid overlaps, end,
  user, order, limit as identifiers anywhere reaching SQL. Same class as
  `zsh: bare SQL is not a command`.

- **Teeth-check, jaccard(), `&` -> `|`. Predicted 2 of 4 catch. EXACT.**
  identical passes (intersection == union on equal sets), disjoint fails,
  partial fails, empty passes (guard short-circuits before the operator).
  The two passes are STRUCTURAL, not weak assertions: no equal-set input
  can distinguish `&` from `|`, and no guarded input reaches the operator.
  Same class as pick_keeper()'s documented one-member limitation.
  Scope caveat: proves sensitivity to THIS break only. `&` -> `-` would
  produce identical failures; `|` -> `^` in the denominator would fail
  partial but pass disjoint.

- `echo ${#VAR}` passes on a shell variable whether or not it is
  exported. `set -a` does export, so the gate is fine — but a check
  reconstructing a code path is a different code path. The check that
  matches what Python does is
  `python -c "import os; print(len(os.environ['VAR']))"`.

- Fatigue: 2 one-token errors (`raising:an`, a trailing comma in SQL).
  Session closed per 06 §13, resumed after a 5-hour break.


## 2026-08-22 — Day 23. BM25, complete.

- **03 §7's numbered tokenization list is an OUTPUT description, not an
  execution order — and following it literally is impossible.**
  Lowercasing at step 1 destroys the camelCase boundaries step 3 needs.
  Treating `_` as non-alphanumeric at step 2 destroys the whole
  identifier step 4 requires. Working order: extract preserving case
  and `_` -> emit lowered whole -> split while case is intact -> emit
  lowered parts IF the split produced more than one. Doc-revision batch.

- **A regex without a quantifier is legal Python and a valid pattern.**
  `_IDENTIFIER` shipped first without `+`, then without `_`.
  `ruff format` reformatted it. `ruff check` passed it. **Regex patterns
  are STRINGS — the linter, the formatter and the type checker all treat
  them as opaque text. The only thing that inspects a regex is running
  it.** New instance of the reference-location defect class: correctly
  written, syntactically legal, semantically wrong, invisible to tooling.
  Caught in 4 seconds by printing output on 3 inputs (invariant 20), on
  the module 07 §2 flags as the silent one.

- **`def build_bm_25_index` vs the spec's `build_bm25_index`.** This one
  would have been SILENT had the call site been typed to match the
  definition — a legal function whose name disagrees with the spec and
  every other reference. Mitigation already on record:
  `grep -rn SYMBOL .` after moving any name.

- **`score > 0.0` guard: discussed, agreed, never reached the file.**
  53 tests passed and 53 was CORRECT — no test existed that could see
  the difference. **Sibling of the reference-location class: the
  decision-never-landed class.** Both are legal code, both invisible to
  tooling, both caught only by an assertion that encodes the intent.

- **Document lengths, 3,196 docs.** mean 146.2, median 102, p90 303,
  max 3,428 (#7930), min 4 (#1148), zero-token docs 0.
  Predicted mean ~200 / median ~150 — both ~30% high. Carried an
  intuition from a 3-document sample that happened to contain a 432.
  **Third instance this week of small samples pulling the estimate
  toward whatever landed in them.**
  Mean sits 43% above median. **avgdl is DEFINED as mean document length
  — BM25's length correction is a sum-normalizing term, not a
  description of a typical document. This is the median/mean lesson
  appearing where MEAN is correct.** With b=0.75, more than half the
  corpus receives a length BONUS and the top decile absorbs the penalty.

- **BM25 index build: 7,558 ms for 3,196 docs. Predicted 400-900 ms —
  8-19x, the worst gap of the session.** 03 §7 claims "at ~1,000 PRs
  this takes well under a second"; scaling linearly predicts ~3 s, so
  the corpus-size ratio does not explain it. Either BM25Okapi
  construction is superlinear in practice or the claim was never
  measured. Push-back protocol: measured, does not hold, reopened.
  40.9 MB tracemalloc peak — Python allocations only, no numpy buffers,
  so a floor. 7.6 s is also a floor: macOS ARM, localhost, warm Postgres.

- **rank-bm25's negative-IDF floor is `epsilon * average_idf`, NOT zero.
  Confirmed from source after I asserted otherwise from memory.**
  `_calc_idf`: idf = log(N - df + 0.5) - log(df + 0.5); negatives are
  replaced by eps. Measured: average_idf 7.0609, epsilon 0.25,
  **floor 1.765**. A df=1 term scores 7.66, so **the floor is 23% of a
  maximally rare term** — handed to words BM25's own formula says carry
  no information. The floor is set by how rare the AVERAGE vocabulary
  term is (19,442 terms, mostly rare), which is why it lands so high.
  **13 floored: the to of and in is for a this js p5 p 5.**

- **This broke 5 of 6 new tests before it was understood.** A 2-document
  fixture where the query term appears in both gives df = N, so
  log(N - df + 0.5) = log(0.5), negative — and with every IDF negative,
  average_idf is negative, so the floor is negative too. Everything
  scored <= 0 and the `score > 0.0` guard emptied the result.
  **The guard was correct; the fixtures were degenerate.** Fixed by
  padding to 20+ unrelated documents, which is the regime BM25 is
  defined for.

- **get_scores iterates the RAW query list** (`for q in query:`), and
  tokenize preserves repeats. **Query term frequency MULTIPLIES the
  score.** A query document saying p5 six times contributes 6 x 1.765
  before length normalization. Confirmed from source.

- **`score > 0.0` drops only 3 of 3,196** on a real query (#9031).
  Nearly a no-op. Correct, free, provably lossless — but the top-50 cut
  does all the work, not the guard.

- **Teeth-check, bm25_signal(), cut-then-filter. Predicted 1 of 6.
  EXACT** — returned 1 candidate where 3 were available.
  **Five reasonable-looking assertions were blind to the one bug in this
  function that produces no traceback**, because each used a corpus
  smaller than its cut, making the cut a no-op. The one that caught it
  was built so the INELIGIBLE documents scored HIGHEST — which required
  knowing BM25's length normalization favours short documents.
  **A suite does not catch a bug class by having many tests. It catches
  it by having the one designed against the mechanism.**

- **Corpus cases worth keeping for the write-up.**
  **#1148**: title `Fixes #1145`, no body, 1 file -> 4 tokens, one of
  which is the issue number. At b=0.75 against avgdl=146 that document
  gets ~1.8x the score of an average-length one for the same single term
  match. Not a bug — length normalization doing its job — but a terse PR
  sharing an issue number can outrank a substantive one.
  **URLs are ~28% of #9032's tokens.** One GitHub permalink becomes 12
  tokens. IDF kills their relevance contribution, but BM25 divides by
  |D|/avgdl — so a PR cross-referencing three issues is penalized on
  LENGTH for tokens carrying no information. **The penalty tracks the
  author's linking habits, not the content.** `4586205003` appears in
  exactly one document: maximal IDF, zero matching power, pure
  length-divisor weight.
  **The p5.js PR template appears verbatim in bodies.** Same mechanism:
  a PR that kept the checklist is penalized relative to one that deleted
  it.

- Fatigue: 4 one-token errors across the evening, all in linter-blind
  positions — an import list, two regex strings, a function name.
  Comprehension was fine throughout; the p5 fragmentation and the 03 §7
  build-time gap were both diagnosed from output immediately. Typing
  degraded, understanding did not.

  ## Day 24 — Session A (2026-08-22)

**Reference-location defect, 3rd instance.** `FILE_CANDIDATES_SQL` and
`jaccard()` both existed, both documented, both correct — and nothing called
them. No production path for the file-overlap signal existed. Handoff recorded
Jaccard as "fully implemented" on Day 21; true of the pieces, false of the
signal. `grep -rn SYMBOL .` found it in four seconds. **Mitigation works when
run.**

**`ruff check` passes an import of a symbol that does not exist.** `scoring.py`
imported `FILE_OVERLAP_TOP_K` before it was added to `constants.py`. F401 is a
purely local check — "bound at module scope, never referenced here." It never
opens the imported module. Three consecutive clean `ruff check` runs; caught by
`pytest` collection. **Same axis all day: absence and redundancy are invisible;
only wrongness that executes gets caught.**

**Corpus file-count distribution measured for the first time.** median 1,
p90 7, max 274, n 3,196.

**⚠️ Jaccard partially degenerates on this corpus.** Half of all PRs touch
exactly one file. For a 1-file query, the intersection is always exactly 1, so
`J = 1/|B|` — the numerator is a constant and Jaccard stops measuring *which*
files are shared, measuring only how focused the candidate is. `03 §6`
documents the hot-file bias; it does not document this. **New named limitation.**

**PREDICTION (mine, unregistered — process failure, logged as such).** Distinct
Jaccard values for #8994: "well under 30." **ACTUAL 48.** Wrong by 60%. Cause:
reasoned from the median-of-1 degeneracy after deliberately picking a 3-file PR
to escape it. `|A|=3` gives three possible numerators. **Same error class as
the last three misses — reasoning from a distribution that did not apply to the
sample.**

**Fan-out for #8994: 148** (Day 22 median 103). Histogram: 0.3333 ×48,
0.6667 ×25, 0.2500 ×10, 0.1429 ×6, then a long thin tail.

**25-way tie for first place.** All at exactly 0.6667 = 2/3, all `files=2`
source+test pairs. Under `03 §8` all 25 normalise to 1.0 and receive an
identical 0.30 of final score, with `RESULTS_RETURNED = 3`. **File overlap
cannot rank this query — it can only nominate.** Which three surface is decided
entirely by vector and BM25. This is a stronger argument for hybrid retrieval
than `03 §4`'s hypothetical, and it is measured.

**Uncapped-return decision validated on first run.** 148 fetched, 100 admitted;
48 retain real scores for backfill instead of a fabricated 0.0.

**Hypothesis withdrawn.** Predicted only #8994 touches
`src/math/patch-vector.js` → "a file created by the query PR is pure
denominator." **Actual: 6 PRs.** Query omitted `in_corpus` and `created_at`, so
it counted PRs the signal never sees. Why no candidate reached k=3 is
**unexamined**. Reasoning was sound; the premise was invented.

**Teeth-check, `build_candidate_set()`, union → intersection: 1 of 2 caught.**
`test_union_...` fired. `test_query_pr_never_retrieves_itself` cannot fail —
`42` is in no input dict, so the assertion is unfalsifiable by construction. It
documents the invariant; it does not defend it. **Known-weak, recorded as such.**

**Fatigue.** Two-error threshold passed by mid-session. Prose garbles through
piece 1–3, then a 5-space indent on `scoring.py:28` — first crossing from
linter-blind prose into the parser. Comprehension stayed intact all day;
typing degraded monotonically.

---

## Day 24 — Session B (2026-08-25, +2 days, emergency)

**Ledger drift.** Handoff and `DECISIONS.md` recorded **126** open PRs.
Measured: **105**. Unexplained. Caught before it reached the `01 §2` amendment.

**PREDICTION (mine) miss.** Predicted open PRs cluster in the last two months
→ eligible for almost no queries → D-P2-12 nearly moot. **Actual span
2021-03-25 → 2026-08-02.** The miss was informative: "open" conflates active
work with long-abandoned-but-never-closed, and the second group is eligible for
five years of queries.

**`normalize.py` written and tested.** 5 tests, 61 → 66. Teeth-check on three
mutations, **1 of 5 caught each, no overlap, none uncaught** — clean separation,
unlike `test_scoring.py`.

- `values = list(raw.values())` → `test_extra_keys` only. Output `0.005, 0.01`
  instead of `0.5, 1.0`: **one outlier at 1000.0 compressed the real range into
  the bottom 1% of the scale.** With `&&` fan-out reaching 1,835, this would be
  most queries, silently.
- `hi == lo → 1.0` → `test_degenerate` only.
- delete the `missing` block → `test_missing_candidate` only.

**⚠️ Mutation C failed with `KeyError: 3`, not `ValueError`.** Deleting the
entire `missing` block still refuses to run — `raw[pr_id]` raises on the first
absent key regardless. **The block is not what makes invariant 2 enforceable;
it is what makes it legible.** `KeyError: 3` says nothing; "missing 1 of 3
candidates: [3] — 03 §4 step 6 backfill did not run" says which stage failed.
The test caught the mutation for a reason other than the one it documents —
noteworthy because that usually goes the other way.

**Float trap avoided by checking rather than assuming.** `0.50+0.30+0.20 == 1.0`
exactly, as do 0.45/0.35/0.20, 0.55/0.25/0.20, 0.40/0.35/0.25. But
`0.7+0.2+0.1 == 0.9999999999999999`. An `== 1.0` guard on invariant 5 would
pass today and **fail at Day 34 after weights are locked**, as a crash that
looks like a scoring bug. Used `math.isclose(..., abs_tol=1e-9)`.

**66 tests passed while `scoring.py` carried seven F821s.** `rank_candidates()`
was valid Python with an undefined name and no caller. **A green test count
describes the code that runs, not the code that doesn't.** Invariant 20's
"never infer correctness from the absence of an error" applies to test counts.

**Naming slip, the safe kind.** `def rank_candidates(candidate: ...)` with six
body references to `candidates`. Unresolvable → ruff sees it instantly.
Contrast Day 21's `values = max(scores)` — bound and referenced consistently,
wrong anyway, invisible. **A name wrong everywhere is safe; a name wrong
nowhere but meaning the wrong thing is the dangerous one.**

**⚠️ `--fix` refused three times.** F401s on `BM25_TOP_K`, `FILE_OVERLAP_TOP_K`,
`VECTOR_TOP_K`, then `min_max_normalize`. All were pending-use, not dead.
**A linter reports the current state; it has no model of the intended one.**
Mirror image of the `FILE_CANDIDATES_SQL` defect — same tool, opposite error,
neither carrying information about correctness.

**Day 25 — `rank_bm25.get_scores` verified from source (flagged unverified
Day 23).** Confirmed: `for q in query:` iterates the raw list. No `k3`
query-saturation term exists in the library. Document TF saturates, query
TF does not. The Day-23 flag was correct. D-P4-9 opened.

**Day 25 — D-P4-5 severity re-derived, and my first framing today was
wrong.** I asserted that floored near-universal terms contribute ~zero and
that the harm was document-length inflation. The Day-23 measurement already
refuted this: the floor is `epsilon * average_idf = 1.765`, not zero. The
first-order harm is term-weight manufacture; length inflation is
second-order. Caught by searching the record instead of reasoning from
scratch. **Second time this project that a stated fact about `rank-bm25`
was wrong from memory** (Day 23: "floors negative IDF at zero").

**Day 25 — teeth check, D-P4-5 tokenizer. PREDICTION EXACT, 3 of 3.**
Break: `len(p) > 1` -> `len(p) > 0`. Predicted 2 of 3 tokenizer tests fail,
`keeps_bare_digit_run` blind, 0 of 6 BM25 golden assertions fire, 67
passing. All four held. Diffs were the intended diffs
(`['p5vector','p','5','vector']`, `['webgl2','webgl','2']`), so the tests
fail for the reason written, not incidentally. Contrast Day 18, where the
same ritual predicted 1 and got 2.

**Day 25 — the six BM25 golden assertions were structurally blind to this
defect.** 0 of 6 fired under the break because no fixture contains a
digit-bearing identifier. They "survived" the Day-24 `bm25_scores` refactor
without ever being able to see tokenizer output shape. Green results reveal
nothing about what a test cannot see — third instance of complementary
blindness (Day 18, Day 23, Day 25).

**Day 25 — prediction, BM25 re-measurement after D-P4-5.**
`avgdl` 146.2 -> 130–138. `average_idf` 7.06 -> rises slightly (two
near-universal terms removed from a 19,442-term vocabulary lifts the mean),
so the 1.765 floor rises with it. Floored set 13 -> 11: `p` and `5` gone,
`p5` survives as a whole identifier and stays near-universal.
Falsifier: if `average_idf` moves more than ~2%, the
"2 of 19,442 terms" reasoning is wrong and something larger changed.

**Day 25 — BM25 re-measurement after D-P4-5. Prediction held 4 of 4.**
avgdl 146.2 -> 135.66 (-7.2%), median 102 -> 94, p90 303 -> 282,
max 3,428 -> 3,418, min 4 unchanged, zero-token docs 0.
average_idf 7.0609 -> 7.0636 (+0.04%), floor 1.765 -> 1.766.
Floored 13 -> 11: `p` and `5` gone, `p5` retained. Max idf 7.66 unchanged.
**Vocabulary 19,442 -> 19,441 — one term, not two.** One of `p`/`5` still
occurs as a standalone whole identifier, which the filter never touches
by design. Trade-off line in D-P4-5 confirmed by measurement.
⚠️ "average_idf rises slightly" was under-specified — direction-only
claims are nearly unfalsifiable. The +/-2% falsifier did the work.
Apply to the Day-34 weight-tuning predictions.

**Day 25 — step 9 corrected my own Day-18 framing.** The 38% censoring
statistic describes NOMINATION, not scoring. `VECTOR_BACKFILL_SQL` has no
LIMIT, so every candidate returns a row for every query embedding and
`chunk_hits` is constant in the scoring path. Consequence: the Day-34
`max` vs `mean_top_k` comparison must run on backfill output, not nomination
output — otherwise it compares strategies over a censored sample and reaches
a conclusion that does not hold in the system.

**Day 25 — third instance of complementary blindness.** 0 of 6 BM25 golden
assertions fired under the tokenizer break; no fixture contains a
digit-bearing identifier. The same six were 5-of-6 blind to the Day-23
ordering bug. They "survived" the Day-24 refactor without ever being able to
see tokenizer output shape.

**Day 25 — the ritual found more than the code did.** Steps 6–9 produced
D-P4-10 and D-P4-11, neither visible while writing the module. D-P4-11 is
behaviour-changing. Argues against ever deferring these to an end-of-project
pass.

2026-09-18 (Day 26) — Temporal filter tests landed. Predictions held:
72 passed / 1 skipped, unit 69.

Three one-token transcription errors in one block: BM250kapi (zero for O),
a missing trailing comma, and timezone.utc surviving three fix passes.
Fatigue rule invoked; teeth check deferred rather than breaking
VECTOR_SIGNAL_SQL after midnight.

Lesson: a SyntaxError's reported line is where the parser gave up, not
where the fault is. Missing comma on 174 reported at 175.

Unrun: the three deliberate breaks. Nothing here has been seen red.

## Day 27 — teeth check, temporal filter tests (predicted with Claude)
| Break | Predicted | Actual | Failing tests |
| 1 vector `<`→`<=` L54 | 2 (vector + candidate-set) | | |
| 2 file `(p.id<>$4 OR TRUE)` L241 | 0 — strict < already excludes query PR | | |
| 3 bm25 `<`→`<=` L437 | 1 (bm25_scores test) | | |
Note: deleting L241 outright would crash on param count — false positive.

Day 27: teeth check 3/3 held (2/0/1). Test docstrings over-claimed
`query` catching the id clause — false while < is strict. Zero-chunk
in-corpus PRs: 0 (raise kept). Gotchas: ingest.db.connect is an
@asynccontextmanager (async with, not await); pgvector decodes to
pgvector.Vector, not ndarray (.to_numpy()). First orchestrator run #8994:
|C|=143, V∩F=32 V∩B=12 F∩B=25 all=12, backfill 135.6 ms / 897.2 total.

- Day 28: Doc 12 ritual on normalize.py + scoring.py. Sharpest point: the degenerate-case 0.0 matters for 03 §10 reason thresholds, not for ranking. The docstring undersells this.
- Day 28: Area:* labels cover 6.7% of the corpus and stop around 2023. D-P5-2 failed on contact with the data.
- Day 28: about 1/3 of src/ PRs in the main strata change only comments (JSDoc lives in src/). A real fact about p5.js; one README line.
- Day 28: formatter-only PRs (#8459) passed the first code filter. Fixed with a normalized compare. Golden predictions matched.
- Day 28: #5460 (docs PR) slipped through the frozen filter. Kept, not re-picked. The freeze matters more than one clean query.
- Day 28: false alarm on a ledger "deletion". It was the missing final newline. Keep a newline at EOF.
- Day 28: ingest.db.connect() is an async context manager (use `async with`). Claude guessed the signature wrong.

- Day 29: #8994 baseline at default weights: #8259 0.9255, #6222 0.8914, #8821 0.8850 (|C|=143). D-P4-14 refactor must reproduce exactly.

- Day 29: D-P4-14 shipped. Refactor reproduced #8994 baseline exactly (stash → run HEAD → pop). Day 27 never recorded the top 3; a baseline you didn't record is one you don't have.
- Day 29: teeth check on key-set test: weakened to subset check → "DID NOT RAISE". Confirms nothing downstream catches extra keys.
- Day 29: invariant 5 gap: sum-to-1 bounds [0,1] only with non-negative weights. Weights now rejects negatives.
- Day 29: per-stage timing on #8994: vector nomination 596 ms (71%), backfill 124, BM25 119, file 2, rank 0.2. Hypothesis: one exact scan per query chunk (15). Verify in Phase 7.
- Day 29: `git add -u` swept in-progress scoring.py into a "style" commit (e8229b3). Stage by path when WIP exists.
- Day 29: zsh doesn't treat inline `#` as a comment — passed as args to select_queries. No comments in commands.
- Day 29: gate pasted as one block let commits run past a failed `ruff format --check`. Read gate output before moving on.

- Day 30: #7978 file_overlap contributed 0 — no past PR touches strands_api.js or the new noise3D shader. Verified by SQL before trusting it. The raw > 0 rule fired exactly once in 20 queries.
- Day 30: censoring check 0/120 — nomination depth 50 vs pool depth 6 absorbed all censoring.
- Day 30: pool = 345 (not ~300). Variant disagreement drives pool size.- Day 30: teeth check on pool evidence rule: norm-based filter passed 6/7 tests. Raw 0 and norm 0 agree in obvious cases; only a test built for the subtle case catches it.
- Day 30: pool.json landed in eval/, but 04 §3 says eval/artifacts/. Should have checked the folder layout before choosing a path.
- Day 31: schema drift — D-P5-1 (Jul 28) added judgments.self_authored to 02 §7, but 001_init.sql was never updated. A decision that changes a spec needs a migration in the same breath.
- Day 31: self-authored pairs in the pool: 0/345. The D-P1-2 familiarity cost never reaches the labels.
- Day 31: reached the first judgment and couldn't grade it — 01 §7 anchors still FastAPI-era (D-P5-2 rewrite owed since Day 25, never carried into a HANDOFF). Caught at count 0, not after 170 labels.
- Day 31: PR template <!-- --> comments ate the 700-char body budget; stripped before judgment 1.
- Day 31: corpus has 41,899 chunks, not invariant 11's "~10k". Likely explains vector nomination 596 ms (15 query chunks x exact scan). Revisit ANN decision with measurements in Phase 7.
- Day 32: manual entry is a transcription channel — first 36 pairs produced one copied-emoji reason. Bulk import from a committed file removed the channel and left a provenance record.
- Day 32: a heredoc saved into a file instead of run in the terminal put the command lines inside the data; caught by the parser's 4-field split before any DB write.
