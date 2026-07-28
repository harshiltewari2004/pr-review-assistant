# PR Review Assistant — Workflow

**v1.1 — Locked July 2026**

*Changed from v1.0: §11's example updated after the Hugging Face pricing change retargeted deployment to Cloud Run.*

How to build this project, distilled from a retrospective of the CF Tracker build — 27 chats over 10 weeks, with the rituals that held and the ones that quietly died.

Every rule here is evidence-backed, not invented. Where a rule exists, the CF failure that produced it is named.

**This document amends** `06_code_standards.md` (session discipline), `07_testing.md` (golden assertions), `09_timeline_and_milestones.md` (estimate calibration, replayability), and `05_frontend.md` (design-before-build).

---

## 1. Session shape

The single most transferable artifact from CF Tracker was the **handoff block** — a context paragraph written at the close of one session and pasted as message one of the next. It survived 26 handoffs.

**It lived only in chat scrollback. That was the mistake.**

### `HANDOFF.md` — in the repo, not the chat

Overwritten at every session close, committed with the session's work. Getting up to speed becomes `cat HANDOFF.md`, not a search across dozens of conversations. It is also diffable, so you can see what you carried forward and never closed.

```markdown
# Handoff — <date>, end of <session subject>

## Done and committed
- <what shipped, with commit refs>

## Deployed state
- Service: <deployed? green/red, last deploy>
- Neon: <schema version, corpus size>

## Open decisions carried forward
- <verbatim, not summarized>

## Carried-over obligations
- <things promised and not yet done>

## Decisions log watermark
- Current through D-P<N>-<M>, committed

## Next session starts with
- <the single next action>
```

### Session open

1. **Paste `HANDOFF.md`.** Message one, verbatim.
2. **Gate.** Confirm the previous piece is deployed green and committed *before* writing new code.
3. **Pre-work capture.** Hit the endpoint, dump the payload, audit it field by field before designing anything against it. On CF Tracker this became mandatory after a bare-ObjectId discovery mid-build.
4. **Architecture question.** You propose, Claude challenges once, two rounds maximum, converge.
5. **Draft → type → predict → verify → commit → log the decision.**

### Session close

**End the session at the commit.** Every decisions-log gap, every bundled commit, every skipped prediction on CF Tracker happened in the stretch *after* the code worked and *before* stopping.

`commit + log the decision + write HANDOFF.md` is the last thing you have energy for — not the thing you do while tired.

The debrief questions (2–3 interview-style) held on CF Tracker only sometimes; unanswered ones accumulated into a backlog spanning weeks. **Answer them in the session or drop them — do not carry them.**

---

## 2. Chat naming

CF Tracker used `phase 6 part 2`. The convention drifted immediately: Week vs Phase labelling for the same work, decimal outliers, casing chaos, and — the expensive part — **no title ever named the subject.**

Consequence: finding a prior conversation required keyword search rather than a glance at the sidebar. One session opened with three separate searches just to recover a payload shape.

**Rule: name by subject.**

```
P2 — diff chunking parser
P5 — blind labeling CLI
P6 — per-query normalization
```

The phase number is the least searchable thing about a session. Put the subject first if it helps.

---

## 3. Code generation — split by tier

CF Tracker's rule was to type every line manually, never copy-paste. It taught real things about engine logic. It taught nothing about config files and cost a steady drip of casing, brace, and quote-character bugs.

**Type logic. Paste plumbing.**

| Type manually | Paste |
|---|---|
| `chunking.py` — the `@@` parser | `config.py`, `db.py` |
| `normalize.py` | Dockerfile, `docker-compose.yml` |
| `signals.py`, `scoring.py` | `migrations/001_init.sql` |
| `eval/score.py` | `requirements.txt`, `pyproject.toml` |
| `reasons.py` template rules | Frontend CSS boilerplate |

The learning goal and the error tax point the same direction here.

### Draft size

**Logic-heavy files get built piece by piece, not as one draft.** On CF Tracker, the engines built as 4–5 sub-pieces had the highest quality and the lowest rework. The one long draft requested under fatigue needed a full architectural reversal afterward.

For this project: `chunking.py`, `scoring.py`, and `eval/score.py` are built in pieces. Never one 80-line draft.

**Long drafts have a direct transcription cost.** One missing character in a CF Tracker draft produced 29 cascading errors.

### Prefer surgical edits

Before any expensive operation, ask for exact line-by-line edit instructions rather than general guidance. Re-running a 3-hour index because of a vague fix is the failure mode.

---

## 4. The fatigue signal

CF Tracker produced, in a single long session: a dropped `*`, a comma where a function call belonged, a temporal dead zone from declaration order, a plural typo, a brace-vs-no-brace import error, and an unquoted string. All in one sitting. It was correctly diagnosed in-session: *fatigue, not a comprehension gap.*

The symptoms always appeared in this order:

1. **Transcription bugs cluster**
2. **You start asking to skip engagement** — *"just give me the file and line from now on"*
3. **Commit hygiene degrades** — feature and fix bundled together
4. **Decisions log entries get skipped**, then reconstructed archaeologically later

**Rule: the second one-token typo in a session is the end-of-session bell.** Not something to push through. Commit what works, write the handoff, stop.

**Corollary that CF Tracker got right:** when you catch yourself asking *"should we start X in this chat or a new one?"* — the answer is always a new chat. That instinct was correct every time it fired.

---

## 5. Debugging

CF Tracker's evidence is unambiguous: **loud bugs were cheap, and every expensive bug was silent.**

| Loud — 1 to 3 turns | Silent — hours to days |
|---|---|
| Typos that throw | A field name that a strict-mode ORM silently drops |
| Import errors | A comma instead of a space in a projection string |
| Missing `await` that returns a promise | A wrong hook with an identical return type |
| Dimension mismatches | A backtick vs a single quote in a template key |

The pattern: **expensive bugs are the ones where both the type system and the runtime stay quiet.**

### The equivalents on this project

Every one of these will fail silently:

- **Chunking** — a hunk parsed with the header intact, or `@@` inside content splitting a hunk incorrectly. Output looks plausible.
- **Normalization** — applied twice, or not at all. Ranking just gets quietly worse.
- **Temporal filter** — a leak returns *better-looking* results. Nothing errors.
- **Corpus filter** — `lang-all` matched but `lang-fr` missed. Retrieval fills with translation PRs.
- **Embedding** — truncation with no warning. Vectors are real numbers, just wrong.
- **Aggregation** — `MAX` over the wrong axis. Still returns a float.

**Rule: after every stage, print and read the output. Do not infer correctness from the absence of an error.**

### The second expensive category — dirty environment

CF Tracker lost days to this, none of it code: stale environment variables in the deploy dashboard, a free-tier Redis auto-deleted after inactivity, six stale test profiles causing a misdiagnosis, a seeded fallback value that skewed reasoning for weeks.

Equivalents here: a stale `DATABASE_URL` in a deployed service's config, a partially-indexed corpus from an interrupted run, a schema divergence between local Postgres and Neon, `seed_results.json` generated under old weights.

**Before debugging logic, verify the environment.** Corpus count, schema version, which weights are loaded, which database you are actually connected to.

---

## 6. Make expensive operations replayable — before the first run

**The single highest-payoff rule for this project.**

CF Tracker ran a 3-hour cohort scan three times, because each write-path bug required a full rescan to discover. The disk cache that made subsequent runs instant was built at run three, not run one. Cost: roughly 6 wasted hours.

**Every long operation here gets a checkpoint before its first execution:**

| Operation | Duration | Checkpoint |
|---|---|---|
| GitHub PR + diff fetch | Hours | Raw API responses to `.cache/prs/` — never re-fetch to fix a parsing bug |
| Embedding the corpus | Hours | Resumable via `UNIQUE (pr_id, file_path, hunk_index)` — already specified in `02` §5 |
| Pool construction | Minutes | Pool written to disk; labeling reads the file |
| Weight tuning sweeps | Minutes each | Judgments loaded once; sweep runs in memory |

**Rule: if a step takes more than ten minutes, build the cache before the first run, not after the first failure.**

The raw-response cache matters most. A chunking bug found after indexing 1,000 PRs should cost a re-parse, not a re-fetch against a rate-limited API.

### Time estimates

CF Tracker's estimates ran **4–7× too low** on multi-hour operations. Treat every duration in `09_timeline_and_milestones.md` as optimistic on anything involving network I/O or model inference.

---

## 7. Verification rituals

CF Tracker built a genuinely good set. Some held; two eroded at a predictable point.

| Ritual | Fate on CF Tracker | Status here |
|---|---|---|
| **`git diff` before staging** | Held throughout — and paid off, converting *"I installed something?"* into a precise answer | Mandatory |
| **Clean boot before push** | Held, added after a deploy failure | Mandatory |
| **Local build before push** | Held, added after type errors reached production undetected | Mandatory |
| **Teeth-check** — deliberately break the code to prove the test detects failure | Held | Mandatory on eval scoring |
| **Payload capture + field audit before building against an API** | Held well | Mandatory |
| **Predict-before-reload** — state expected values *before* running | **Eroded around week 6.** Flagged four-plus times. Always slipped under time pressure, never under confusion | See below |
| **Decisions log at commit time** | **Eroded around week 6.** Required a full audit that found 5 missing entries, a broken heading, 8 stale open markers | See below |

### The two that erode, and when

Both died around **week 6** on CF Tracker. This project's week 6 is roughly **Phase 5–6 — labeling and weight tuning.** That is precisely the phase where a skipped prediction is most expensive, because the numbers are the deliverable.

**Predict-before-reload, applied here:** before running the eval harness, write down the Recall@3 you expect. Before running retrieval on a known query, name the PR you expect back. A number that surprises you is either a bug or a finding, and you cannot tell which if you had no expectation.

**`DECISIONS.md`, applied here:** logged at commit time, in the format CF Tracker used — `D-P<phase>-<n>`, with status `OPEN` or `CONFIRMED`. Audit it at the end of Phase 6, before the number leaves the repository.

---

## 8. Golden assertions — one per stage, at build time

CF Tracker installed a test framework, wrote one test block, and shipped with roughly that. Not a discipline failure so much as a scheduling one — tests were planned for a later phase that arrived under time pressure.

But the retrospective's own conclusion is sharper: **a full suite would not have caught most of the expensive bugs.** They were silent data-shape bugs, not logic errors. What *would* have caught them is a single assertion pinned to each invariant, written at the moment the invariant was built.

**Rule: three lines per stage, written when you build the stage.**

| Stage | Golden assertion |
|---|---|
| Chunking | Fixture diff → exact expected hunk count, first hunk's `file_path`, header stripped of line numbers |
| Embedding | Output is exactly 384 dimensions, L2 norm ≈ 1.0 |
| Retrieval | Three known query PRs return non-empty results, all predating the query |
| Normalization | Output bounded `[0, 1]`; `max == min` returns all zeros |
| Scoring | `final_score ∈ [0, 1]` with weights summing to 1.0 |

This does not replace `07_testing.md` — it is the minimum that exists from day one regardless of what else slips.

---

## 9. Design the visible thing before you build it

**The most consequential CF Tracker failure, and the most directly applicable.**

The heatmap was the named hero component and the intended interview screenshot. It was built, and its data layer was verified end to end — hundreds of correct rows, memoized grid, explainer confirming the math against real data. Then it was **rejected on aesthetics**: *"I only see it as a color palette… it does not convey something to me."*

Correct self-critique. But it was deferred, then deferred again, and **the hero component never shipped in its intended form.**

The exact same risk exists here. `05_frontend.md` names the **contribution bar** as the signature element — the thing that makes the hybrid argument visible. It is specified in text and has never been seen.

**Rule: before Phase 8, sketch the contribution bar with fake data.** One hour, any tool. If it does not convey what it is supposed to convey, that is discovered for free — not after the pipeline that feeds it is built.

Do this during a Phase 5 labeling break. Labeling is tedious; a design hour is a good interruption.

---

## 10. Read the code before drafting against the spec

CF Tracker designed and drafted a whole engine method against a locked data-models document, then deleted it entirely — the implementation had already moved to a different write strategy, and the new method would have double-counted.

**The locked docs are ground truth for intent. The codebase is ground truth for reality.** They diverge silently.

On this project the docs are newer and will drift faster. Before writing code that touches an existing module, open the module. Before drafting against `03_retrieval_engine.md`, check what `scoring.py` actually does now.

---

## 11. Do not put scheduled work on infrastructure that sleeps

CF Tracker put an in-process scheduler on a free instance that sleeps after inactivity. The job never fired in production. A documented product feature ran for a month with a stale-date badge.

**This was known from week 0 and designed around anyway.**

Here, nothing scheduled runs on the service at all. Indexing runs locally by design (`04_architecture.md` §2), and the keepalive that v1.2 of the frontend doc specified was **removed** once the demo page moved to a static host — there is no longer anything to keep warm.

**If anything scheduled gets added later, it goes on GitHub Actions.** Never in-process on a container that scales to zero.

### A related lesson, learned the hard way on day 1

**A platform's free tier is a fact with an expiry date.** Hugging Face began requiring a paid plan for Docker Spaces in July 2026 — no changelog, no email, visible only as a "Paid" badge in a form. Four documents were written against the old terms.

Two things limited the damage, and both were design decisions made weeks earlier:

- **The evaluation harness is deployment-independent** (`01_evaluation_protocol.md` §15), so no published number depended on where the service ran
- **The demo page was designed to need no live compute** (`05_frontend.md` §5), so the recruiter path survived the change untouched

**Verify a free tier at the moment you depend on it, not at the moment you plan for it.** And keep the parts that matter — the number and the demo — structurally independent of the parts that can change underneath you.

---

## 12. Carry this over unchanged

CF Tracker's best structural habit: **hide the view, keep the engine.** Across the project, work was commented out rather than deleted, descoped with a logged reason rather than abandoned silently, and open questions marked `PENDING` rather than dropped.

That discipline is the only reason a late audit was possible at all — the record was messy, but it was never *missing*.

Keep it. When something gets cut here, it gets a `DECISIONS.md` entry with a reason, not a silent deletion.

---

## 13. Checklist

**Every session**
- [ ] Opened by pasting `HANDOFF.md`
- [ ] Previous piece confirmed deployed green and committed before new code
- [ ] Payload captured and audited before building against it
- [ ] Chat named by subject
- [ ] Stopped at the second transcription typo
- [ ] Closed with commit + `DECISIONS.md` entry + `HANDOFF.md` rewrite

**Every stage**
- [ ] Output printed and read, not assumed correct
- [ ] Golden assertion written at build time
- [ ] Checkpoint built before the first long run
- [ ] Prediction stated before running the eval harness

**Phase gates**
- [ ] Contribution bar sketched with fake data before Phase 8
- [ ] `DECISIONS.md` audited at end of Phase 6
- [ ] Environment verified before debugging any silent failure
- [ ] Existing module read before drafting against a spec doc
