# PR Review Assistant — Timeline and Milestones

**v1.2 — Locked July 2026**

*Changed from v1.1: Phase 1 day 1 is a local build, not a live deploy; Phase 3 adds the memory-footprint measurement that decides hosting; Phase 7 retargeted to Cloud Run.*
*Changed from v1.0: §1 adds estimate calibration; Phase 2 adds the response cache; Phase 5 adds the contribution-bar sketch; Milestone C adds the decisions audit.*

Ninth document in the set. Sequences everything the other eight specify.

---

## 1. Scope of estimate

This timeline assumes:

- **Solo build.** No collaborator.
- **3.5–4 hrs/day, most days.** 50 days ≈ **175–200 hours.**
- **New to the Python/ML/infra half.** Comfortable with JS/frontend, learning FastAPI, sentence-transformers, pgvector, and Docker deployment as you go.
- **Design is already complete.** Phase 0 produced eight locked documents; no design decisions remain open.

**Honest calibration:** a realistic Tier 1 build for someone new to this stack is 160–200 hours. At 4 hrs/day, 50 days is 200 hours. **There is essentially no margin.** The buffer days in this document are not slack — they are where overrun goes, and they will be used.

If you can give 5+ hrs/day, this compresses to ~40 days. At 2–3 hrs/day, plan for 65–70 and adjust the phase boundaries proportionally. The **order never changes**.

### Estimate calibration

On a prior project of comparable scope, **estimates for long-running operations ran 4–7× low** — a step quoted at 20–45 minutes took three hours (`11_workflow.md` §6).

Every duration in this document is optimistic on anything involving **network I/O or model inference**: the GitHub ingest, the full embedding run, and Docker builds under `--platform linux/amd64` emulation on Apple Silicon (10–20 minutes, not seconds). Days 19 and 38 are the two most likely to overrun. Treat the buffer days as already spoken for.

---

## 2. Build order rationale

**Measurement before difficulty.** The hardest work — normalization, weight tuning, hybrid scoring — is deferred until a crude pipeline exists to measure it against. Perfecting the scoring math on day 5 means tuning by intuition for three weeks and discovering on day 30 that the approach caps out. Build the thinnest thing that produces a number, then improve it against a scoreboard.

**Risk before construction.** Four existential unknowns (data access, pgvector, embedding quality, deployment) are killed in week 1 as throwaway scripts. Each costs an evening now and a phase later.

**All three signals before labeling.** The pooling procedure (`01_evaluation_protocol.md` §9) draws candidates from four retrieval variants. Every signal must exist — even crudely, even unnormalized — before a single judgment can be made. This ordering is non-negotiable; skipping it produces an unpoolable evaluation.

**Container early, deployment late.** A skeleton image builds and runs locally on day 1 — proving torch installs, the port binds, and `/health` answers while the app is twelve lines. The service is not deployed anywhere until Phase 7, because **the measurement that decides the host does not exist until Phase 3** puts a model in the lifespan handler. Choosing a host on an estimate is what forced this document to v1.2 in the first place.

**Frontend last.** It consumes an API that must exist and return real results first. Building it earlier means building against mocks that drift.

---

## 3. Phases

### Phase 0 — Design · complete

Eight documents locked: evaluation protocol, data models, retrieval engine, architecture, frontend, code standards, testing, setup.

**Deliverable:** no design decisions remain open.

---

### Phase 1 — Setup and risk spikes · Days 1–7

| Day | Work |
|---|---|
| 1 | `08_setup.md` end to end — accounts, scaffold, migrations on both databases, skeleton image built and answering `/health` locally |
| 2 | **GitHub API spike** — paginate PRs, fetch diffs, handle rate-limit headers and backoff. Save 7 fixture diffs (`07_testing.md` §4) including the `@@`-in-content case. |
| 3 | **pgvector spike** — insert one 384-dim vector from Python, query it back by cosine, against both local and Neon |
| 4 | **Embedding sanity spike, both repos** — known-similar PR pairs from FastAPI (Python) and p5.js (JavaScript), each with a size-matched negative control. Record the gap, not the raw cosine. Resolves `D-P1-2` and `D-P1-4`. Pairs listed in `08_setup.md` §8a. |
| 5–7 | Buffer, or begin Phase 2 early |

**Deliverable:** four throwaway scripts, all four unknowns resolved, `JOURNAL.md` started.

---

### Phase 2 — Ingest and chunking · Days 8–14

Fetch PRs, apply corpus filters, parse diffs into hunks, store metadata.

| Day | Work |
|---|---|
| 8–9 | `ingest/github_client.py` — pagination, rate limiting, resumability, **raw responses cached to `.cache/` before parsing** (`04` §5) |
| 10 | `ingest/corpus_filter.py` — bots, `lang-*`, `docs`, `release`, housekeeping. Mark, never delete. |
| 11–12 | `ingest/diff_parser.py` — hunks by `@@`, header handling, file exclusions. **Write `test_chunking.py` alongside it**, not after. |
| 13 | `scripts/index_repo.py` — wire it together, run on 50 PRs |
| 14 | Buffer |

**Deliverable:** `pull_requests` populated for the full repo; chunking tested against real fixture diffs.

---

### Phase 3 — Embedding and vector skeleton · Days 15–20

| Day | Work |
|---|---|
| 15 | `app/retrieval/embedding.py` — model load, batching, `token_count`, `was_truncated`. **Measure resident memory with the model loaded** (`docker stats` on the container). This number decides the Phase 7 host — record it in `JOURNAL.md`. |
| 16 | Full indexing flow on 50 PRs → chunks with vectors in Postgres |
| 17 | Vector similarity query — top 10 by cosine, temporal filter enforced |
| 18 | Chunk → PR aggregation (`MAX`, with mean-of-top-3 behind a flag) |
| 19 | Full index run on the filtered corpus. Expect hours. |
| 20 | Buffer + **Milestone A** (§4) |

**Deliverable:** given a PR, the system returns 10 vector-ranked past PRs. **First measurable artifact.**

**Tag `v0.1-vector-only`** — this is the reproducible baseline for what hybrid later buys you.

---

### Phase 4 — Three signals, crude · Days 21–24

Deliberately unnormalized and untuned. This phase exists so pooling has variants to draw from.

| Day | Work |
|---|---|
| 21 | File-path Jaccard overlap |
| 22 | BM25 via `rank-bm25` — document construction, tokenization with sub-token splitting |
| 23 | Candidate set as a union across all three signals; naive weighted sum |
| 24 | **Temporal filter test — hard deadline** (§5). Buffer. |

**Deliverable:** four retrieval variants runnable — vector-only, BM25-only, file-only, naive hybrid.

---

### Phase 5 — Labeling · Days 25–31

The phase most people skip when time gets tight. Do not skip it.

| Day | Work |
|---|---|
| 25 | Select 20 query PRs, stratified across ≥6 subsystems. Build `eval/pool.py`. |
| 26–31 | **During any labeling break: sketch the contribution bar with fake data** (§4, Milestone B′). One hour, any tool. |
| 26 | `eval/label.py` — blind CLI, shuffled, records grade + reason + seconds |
| 27–28 | **Batch 1** — 10 queries, ~150 judgments |
| 29 | **Self-agreement check on batch 1.** Revise the rubric if agreement is poor. |
| 30–31 | **Batch 2** — 10 queries, ~150 judgments |

**Deliverable:** ~300 judgments in `judgments.jsonl`, tune/holdout split fixed in the database.

---

### Phase 6 — Hybrid and the locked number · Days 32–37

| Day | Work |
|---|---|
| 32 | `normalize.py` — per-query min-max, degenerate case handled |
| 33 | `eval/score.py` — Recall@3 strict and lenient, MRR, bootstrap CI |
| 34 | Weight tuning **on the tune split only**. Compare `MAX` vs mean-of-top-3. |
| 35 | **Lock weights.** Record the date in `constants.py`. |
| 36 | **Run the holdout — exactly once.** Compute kappa. |
| 37 | Buffer + **Milestone C** (§4) |

**Deliverable:** the number that goes on the resume, with its confidence interval and self-agreement rate.

**Tag `v0.2-hybrid`.**

---

### Phase 7 — Deploy and Action · Days 38–42

| Day | Work |
|---|---|
| 38 | Real service on **Cloud Run** — CPU-only image, `--platform linux/amd64`, US region, model baked in, Neon pooled connection, secrets via Secret Manager, CORS for the static origin |
| 39 | `POST /analyze` and `GET /similar/...` live |
| 40 | GitHub Action — warmup loop, `continue-on-error`, comment formatting |
| 41 | Test on your own fork. Fix formatting and edge cases. **Record the GIF.** |
| 42 | `scripts/generate_seeds.py` — precompute the three demo queries. **Measure the Cloud Run cold start.** Artifact Registry cleanup policy. Buffer. |

**Deliverable:** a real bot comment on a real PR. This is the artifact everything else points at.

---

### Phase 8 — Demo frontend · Days 43–47

| Day | Work |
|---|---|
| 43–44 | Build it — seeded rendering, query input, result cards, contribution bar |
| 45–46 | **Design iteration.** This is where your differentiation lives; it takes passes. |
| 47 | Responsive to 360px, keyboard focus, reduced motion, states, OG tags, `preview.png` |

**Deliverable:** demo page that renders instantly and looks like a product.

---

### Phase 9 — README and final · Days 48–50

| Day | Work |
|---|---|
| 48 | README — **GIF above the fold**, one-line problem statement, comparative metric, demo link. Architecture and methodology below. |
| 49 | Commit eval artifacts, verify `docker-compose up` works from a clean clone, repo public, topics added |
| 50 | Final pass. Resume bullets written. **Tag `v1.0`.** |

**Deliverable:** a repo a stranger can understand in 30 seconds and reproduce in one command.

---

## 4. Critical milestones

Four points where you stop building and validate. Each is cheap here and expensive later.

**Milestone A — Day 20: do the results feel right?**

Take three query PRs you understand well. Run vector-only retrieval. Read the top 10 yourself.

Ask: *are any of these genuinely related?* You are not measuring — you are sanity-checking that the pipeline produces something a human would recognize as reasonable. If every result looks random, something upstream is broken (chunking, embedding, the temporal filter) and it is far cheaper to find here than after 300 judgments have been made against it.

**Milestone B — Day 29: is my labeling consistent?**

The self-agreement check on batch 1. If quadratic weighted kappa comes back below ~0.6, the rubric is ambiguous and **revising it now costs 150 judgments; revising after batch 2 costs 300.**

**Milestone B′ — during Phase 5: does the signature element actually work?**

Sketch the contribution bar with fake data before Phase 8 builds it.

On a prior project, the named hero component was built, its data layer verified end to end, and then **rejected on aesthetics** — *"I only see it as a color palette; it does not convey something to me."* Correct self-critique, but it arrived after the work was done. It was deferred, then deferred again, and the hero component never shipped in its intended form (`11_workflow.md` §9).

The contribution bar carries the same risk: it is specified in text, named as the thing that makes the hybrid argument visible, and has never been seen. **One hour with fake data surfaces "this doesn't convey what I wanted" for free.** Labeling is tedious; a design hour is a good interruption.

**Milestone C — Day 37: is the number honest?**

Before the number goes anywhere, verify: was the holdout evaluated exactly once? Are weights locked with a date? Is the CI computed? Is the `|relevant|` distribution published? Is the kappa reported alongside?

**Audit `DECISIONS.md` in the same pass** — missing entries, malformed headings, stale `OPEN` markers that were resolved and never reconciled. A ledger left unaudited drifts silently; one audited once is trustworthy for the rest of the build.

**A number that fails this check must not go on the resume.**

**Milestone D — Day 41: does it work for someone else?**

Open a test PR on your fork and watch the comment appear without touching anything. If it needs manual intervention, it is not deployed — it is a demo you drive.

---

## 5. Hard deadlines

Two items cannot slip, because slipping invalidates work already done.

**Day 4 — the embedding sanity spike.** The only assumption that could reshape the project. If two known-similar PRs return cosine ~0.2, the vector signal is weaker than `03_retrieval_engine.md` assumes and the weighting needs rebalancing toward file overlap and BM25. That decision is cheap on day 4 and expensive on day 34.

Day 4 now also resolves **`D-P1-2` — primary evaluation repo.** I contribute to `processing/p5.js`, which makes it a candidate primary repo: domain expertise raises label quality, and it merges the "contributor" and "project" narratives into one. The spike decides it. Both pairs reasonable → p5.js primary, FastAPI as cross-language evidence. p5.js weaker → FastAPI primary, p5.js as a measured secondary. Either outcome is a win, because either way the cross-language claim becomes a measurement rather than an assumption.

**The criterion is the gap, set before the run.** Similar-pair cosine minus control cosine, per repo:

| Gap | Reading |
|---|---|
| **> 0.15** | Vector signal discriminates. Proceed as `03_retrieval_engine.md` specifies. |
| **0.05 – 0.15** | Weak but real. Rebalance starting weights toward file overlap and BM25. |
| **< 0.05** | Near-random on code diffs. The vector third needs rethinking before Phase 3. |

Then compare `gap_fastapi` against `gap_p5js` to resolve `D-P1-2`. Comparable → p5.js primary, since domain expertise raises label quality. p5.js materially lower → FastAPI primary, p5.js as measured secondary.

Write the predicted gaps in `JOURNAL.md` **before** running (`01_evaluation_protocol.md` §14). Fixing the thresholds in advance is what stops the result being rationalised after the fact.

**Day 24 — the temporal filter test.** It must exist before Phase 5 labeling begins. A leak discovered afterward means **relabeling ~300 hand-judged pairs.** Everything else in `07_testing.md` can slip; this cannot.

---

## 6. Risk markers

Honest checkpoints. If you hit one, the problem is usually scope, not skill.

| If by… | you don't have… | then… |
|---|---|---|
| Day 7 | all four spikes resolved | You are learning the stack slower than assumed. Extend to 60 days now rather than compressing later. |
| Day 14 | PRs and chunks in the database | Ingest is harder than expected. Cut corpus size — index 500 PRs instead of the full history. Quality of the eval matters more than corpus size. |
| Day 20 | vector-only retrieval returning results | The critical path is blocked. Stop adding anything; fix this before Phase 4. |
| Day 31 | 300 judgments done | Reduce to 15 queries (~225 judgments) and accept a wider CI. **Do not reduce rigor** — reduce sample size and report it honestly. |
| Day 42 | a real bot comment on a real PR | Cut the frontend to a static results page. Deployment proof outranks demo polish. |
| Day 42 | acceptable cold start | Apply `04` §7's mitigations in order. `--min-instances=1` is the last resort — it ends "free". |

---

## 7. Cut order

When time runs short — and it will — sacrifice in this order:

1. **Demo page polish** — ship it plain
2. **The `MAX` vs mean-of-top-3 comparison** — keep `MAX`, note the alternative as untested
3. **Corpus size** — 500 PRs instead of the full history
4. **Query count** — 15 instead of 20, with a wider CI stated
5. **Second annotator** — already optional

**Never cut:**

- The evaluation harness
- The tune/holdout split
- Blind labeling
- Reporting the confidence interval
- The temporal filter

**The evaluation is the project.** A polished demo with an unmeasured claim is a worse artifact than a plain page with a defensible number. If you find yourself trading away rigor to save days, you are cutting the wrong thing — cut scale instead.

---

## 8. After day 50

Not abandoned — a roadmap, in descending order of return:

1. **Merged p5.js PRs** arising from the labeling work. You will read hundreds of PRs building the eval set; bugs you find and fix there turn two resume lines into one story. This is stronger under `D-P1-2` than it was before it: you already contribute to `processing/p5.js`, so the follow-on is continuing existing work rather than opening a cold-start contribution to an unfamiliar repository.
2. **A written artifact** on the metric-switch story — the strongest technical narrative the project produces.
3. **Real users** — even five external repos installing the Action changes it from a demo to a tool.
4. **Code-aware embeddings** (CodeBERT or similar) — re-embed, re-run the harness, report the delta. The harness exists to make this measurable.
5. **ONNX conversion** — smaller image, faster cold start.
6. **Incremental sync**, multi-repo support, LLM-generated reasons.

Items 1–3 raise the project's value more than any further engineering.

---

## 9. Checklist

- [ ] `JOURNAL.md` entry on day 1, and on every day something breaks
- [ ] `HANDOFF.md` rewritten and committed at every session close
- [ ] Raw API responses cached before parsing (Phase 2)
- [ ] Contribution bar sketched with fake data during Phase 5
- [ ] `DECISIONS.md` audited at Milestone C
- [ ] Day 4 embedding spike completed on schedule
- [ ] Resident memory with model loaded measured at Phase 3 and journalled
- [ ] Budget alert set at $1 before any Cloud Run deploy
- [ ] `v0.1-vector-only` tagged at end of Phase 3
- [ ] Milestone A run before Phase 4
- [ ] Temporal filter test written before Phase 5
- [ ] Milestone B run between labeling batches
- [ ] Holdout evaluated exactly once
- [ ] Milestone C passed before the number leaves the repo
- [ ] `v0.2-hybrid` tagged at end of Phase 6
- [ ] Milestone D — bot comments unattended on a real PR
- [ ] Seeds regenerated after weights locked
- [ ] `v1.0` tagged on day 50
