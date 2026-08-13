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