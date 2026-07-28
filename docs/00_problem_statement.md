# PR Review Assistant — Problem Statement and Scope

**v1.1 — Locked July 2026**

*Changed from v1.0: §8 records the hosting change and the cost caveat.*

The foundation document. Every other document in this set answers *how*; this one answers *why*, and fixes what is in and out of v1.

Written last, deliberately — the scope below reflects decisions already stress-tested across the other eight documents rather than an opening guess.

---

## 1. The problem

**A reviewer opening a pull request has no memory of the repository's history.**

They cannot easily know whether this change was attempted before, whether a similar bug was fixed six months ago, whether another contributor made an identical refactor last year, or whether this exact approach was proposed and abandoned. GitHub offers no mechanism to surface that context at the moment it matters. The information exists — it is sitting in the repository's own PR history — but retrieving it requires knowing what to search for, which is precisely what the reviewer lacks.

The cost compounds in three ways:

- **Duplicated review effort.** Two reviewers independently reason through the same tradeoff months apart.
- **Repeated mistakes.** A failure mode surfaced in a past review is rediscovered in production.
- **Re-litigated decisions.** A design debate settled in a closed PR is reopened because nobody remembers it happened.

Mature repositories are worst affected: the more history exists, the more valuable it is and the less accessible it becomes.

---

## 2. What this does

When a pull request is opened in a connected repository, the system finds the **three most similar past pull requests** from that repository's history and posts them as a comment — with a short reason for each, and an explicit flag when a past PR was **closed without merging**.

The tool does not review code. It does not judge correctness. **It gives the reviewer the repository's memory** and lets them decide what to do with it.

### Example output

> **3 related past PRs**
>
> **#15992** — fix: pass include/exclude/by_alias params to jsonable_encoder · *closed without merging — worth checking why*
> Both modify `fastapi/encoders.py` with a similar change pattern
>
> **#15641** — Fix jsonable_encoder crash on invalid UTF-8 bytes · *merged*
> Also changes `fastapi/encoders.py`
>
> **#15476** — Skip set(obj.keys()) allocation in jsonable_encoder · *merged*
> Shares terminology: `jsonable_encoder`, `include`

The closed-without-merging flag is the highest-value output in the system. A past attempt at the same change that did not land is often more useful to a reviewer than three that did.

---

## 3. Who it is for

**Primary: a reviewer on a mature repository.** Someone who did not write the code, may not have been present for the relevant history, and has minutes rather than hours.

**Secondary: the PR author.** Seeing a prior rejected attempt before review begins saves a round trip.

**Not for:** new or small repositories. With little history there is nothing to retrieve, and the tool correctly returns nothing.

---

## 4. Why this problem is worth solving

Three reasons this was chosen over alternatives:

1. **The information already exists and is inaccessible.** This is a retrieval problem, not a generation problem — which means results can be *verified* rather than trusted, and quality can be *measured* rather than asserted.
2. **Quality is measurable.** "Did the right past PR appear in the top 3?" has an answer. That makes a defensible number possible, which is the project's central goal (§7).
3. **It is genuinely non-generic.** Developer tooling for code review is the working domain of companies like Atlassian, where Bitbucket occupies this exact space.

---

## 5. Locked feature scope

Four features. Nothing else ships in v1.

### Feature 1 — Repository indexing

Fetch a repository's PR history via the GitHub API, filter to genuine code-change PRs, parse diffs into hunks, embed each hunk, and store vectors and metadata in Postgres.

Runs as a **local script**, not a service endpoint (`04_architecture.md` §2).

### Feature 2 — Hunk-level chunking and embedding

Each `@@` block becomes one independently embedded unit. Coarser loses granularity; finer loses context (`03_retrieval_engine.md` §2).

### Feature 3 — Hybrid retrieval

Three signals — vector similarity, file-path overlap, BM25 — normalized per query and combined into a weighted score. Chunk-level scores aggregate to PR level. Top 3 returned with template-generated reasons (`03_retrieval_engine.md` §4–§10).

### Feature 4 — GitHub Action with automatic commenting

Triggers on `pull_request: opened`, calls the service, posts the formatted comment. Failure is non-fatal — this tool must never fail someone's pull request (`04_architecture.md` §6).

### Supporting, not a feature

**The evaluation harness** (`01_evaluation_protocol.md`) is offline and ships with the repository but is not part of the running product. It is nonetheless the most important artifact the project produces (§7).

**The demo page** (`05_frontend.md`) exists to make the system visible to someone who will not install an Action.

---

## 6. Non-goals

Each was considered and cut. **Recorded with rationale so they are not silently reintroduced.**

| Not doing | Why |
|---|---|
| **Reviewing code or suggesting changes** | A different and much harder problem. This tool retrieves; it does not judge. |
| **Two-service architecture (Node + Python)** | The entire interesting surface is Python. A second service would add a network hop, serialization, and cross-service failure handling to the *boring* half. |
| **MongoDB alongside Postgres** | Postgres was already required for pgvector. JSONB and array columns cover the document shape. |
| **Webhook receiver** | Redundant with the GitHub Action; both detect PR-open. The Action needs no public callback URL or secret verification. |
| **React admin UI** | Repository management and indexing controls describe operations that moved local. No UI needed for them. |
| **LLM-generated reasons** | Reintroduces the API dependency the local embedding model exists to avoid; makes output non-deterministic. |
| **Incremental sync** | The corpus is a snapshot. A demo repository's history does not change meaningfully day to day. |
| **Multi-repository support** | One well-indexed repository proves the system. Several would strain the free-tier storage budget. |
| **Cross-repository similarity** | Interesting, and a different product. |
| **Authentication and multi-user** | There is one user of the demo page and no personal data in the system. |

**On "rejected" PRs:** GitHub has no rejected state. Any language asserting rejection is a factual error about GitHub's data model, not a copy choice. The system says *closed without merging* everywhere.

---

## 7. Success criteria

The project succeeds if all four hold on day 50:

1. **It runs unattended.** A PR opened on a test repository receives an automatic comment with no manual intervention.
2. **The results are measurably good.** A Recall@3 figure exists, computed on a held-out split, reported with its confidence interval and the labeler's self-agreement rate.
3. **Every claim survives a follow-up question.** Anything on the resume can be defended for twenty minutes — including its limitations.
4. **A stranger can understand it in 30 seconds and reproduce it in one command.**

### What success is not

**Not a high number.** A modest, honestly-reported figure with a documented methodology is a better outcome than an impressive one from a flawed protocol. If the two conflict, rigor wins — see the cut order in `09_timeline_and_milestones.md` §7.

**Not feature count.** Scope was cut deliberately and repeatedly. Depth plus a defensible number is the signal; breadth is not.

---

## 8. Known limitations

Stated here so they are never discovered by someone else first.

| Limitation | Status |
|---|---|
| **The embedding model is a natural-language model applied to code.** A code-aware embedder would raise the vector signal's ceiling. | Deliberate cost/reproducibility tradeoff (`03` §3) |
| **Hunks over 256 tokens are silently truncated** by the model. | Measured and published as a rate (`02` §5) |
| **Relevance is subjective.** The metric measures agreement with a documented standard, not objective correctness. | Quantified via self-agreement kappa (`01` §12) |
| **Small evaluation sample.** 20 queries, 10 held out. Confidence intervals are wide. | Reported, never hidden (`01` §14) |
| **Pooled recall, not absolute recall.** The relevant set is what the pool surfaced, not exhaustive ground truth. | Standard IR practice, stated explicitly |
| **Single-repository snapshot**, no incremental sync. | Scoped decision (§6) |
| **Not strictly zero-cost.** Cloud Run requires a linked billing account even inside Always Free, and Artifact Registry bills past 0.5 GB of stored images. Expected: $0 with a cleanup policy in place. | Budget alert at $1 (`04` §9) |
| **Cold start is unmeasured.** A scale-to-zero service loading torch and MiniLM may take 15–60 seconds on first request. Affects custom demo queries and the Action, never the seeded demo page. | Measured at Phase 3 (`09` §3) |
| **Vector signal validated on Python only.** MiniLM is a natural-language model; its embedding quality on other languages is unmeasured. A cross-language check on p5.js (JavaScript) runs at Day 4. | Measured, not assumed (`09` §5, `D-P1-2`) |

---

## 9. Checklist

- [ ] README's problem section derives from §1–§2
- [ ] Non-goals in §6 are never silently reintroduced
- [ ] "Closed without merging" language used everywhere, never "rejected"
- [ ] All four success criteria met before day 50 is called complete
- [ ] Limitations in §8 appear in the README, not just here
