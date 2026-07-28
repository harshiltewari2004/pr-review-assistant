# PR Review Assistant — README and Presentation

**v1.1 — Locked July 2026**

*Changed from v1.0: architecture diagram now includes the static host; §7 adds the hosting-pivot story.*

How the finished project is presented — README structure, resume bullets, repository metadata, and outreach framing.

Executed in Phase 9 (days 48–50), but written now so those days are transcription rather than design.

---

## 1. The presentation problem

The project's real strengths — the relevance rubric, the tune/holdout split, self-agreement kappa, confidence intervals — are **invisible at screen stage.** A recruiter spends roughly 30 seconds. An engineer scanning a GitHub repository spends perhaps two minutes before deciding whether to read further.

This produces a specific ordering rule:

> **Proof of working first. Methodology second. Rigor rewards the reader who stays.**

The instinct to lead with the evaluation methodology is wrong — it is the most impressive thing here *and* the least legible. Leading with it costs the first thirty seconds and buys nothing.

---

## 2. README structure

### Above the fold — the first screen

Nothing else competes for this space.

```markdown
# PR Review Assistant

Surfaces the past pull requests a reviewer should see before approving a new one.

![Bot commenting on a real PR](docs/demo.gif)

**[Live demo](https://...)** · Hybrid retrieval over X,XXX p5.js PRs
Recall@3 improves XX points over keyword search alone, measured on 300 hand-judged pairs.
```

**Four elements, in this order:**

1. **The GIF.** The bot comment appearing on a real PR. Not an architecture diagram — the actual thing working. This is the single most legible artifact the project can produce, and it belongs first.
2. **One sentence** describing what it does, written for a reader who does not know the domain.
3. **The demo link**, early enough that it is clicked before anything is read.
4. **The comparative metric** (§4).

### Below the fold — in this order

**The problem** — two or three sentences from `00_problem_statement.md` §1. Why a reviewer needs this.

**How it works** — three short paragraphs, plain English, no code: chunking → embedding → hybrid scoring. Someone unfamiliar with retrieval should follow it.

**Architecture** — one diagram. Hand-drawn and photographed is acceptable. Must show the local indexing script, Postgres/pgvector, the Cloud Run service, the **static demo host**, and the Action. The split between the static page and the API is worth drawing clearly — it is why the demo is instant.

**Evaluation** — the most important section for the reader who stayed:

```markdown
## Evaluation

Strict Recall@3: XX% (95% CI: XX–XX) on 10 held-out queries,
over 300 manually judged candidates from processing/p5.js.
Labeler self-agreement: κ = 0.XX.

Relevance was judged against a written rubric ([EVALUATION_RUBRIC.md]),
labeled blind, with weights tuned only on a separate 10-query split.

| Configuration      | Recall@3 | MRR  |
|--------------------|----------|------|
| BM25 only          | XX%      | 0.XX |
| File overlap only  | XX%      | 0.XX |
| Vector only        | XX%      | 0.XX |
| **Hybrid**         | **XX%**  | 0.XX |
```

**That table is the strongest single element in the README.** It shows the hybrid claim was tested rather than asserted, and it makes the improvement immediately visible.

**Limitations** — from `00_problem_statement.md` §8. A named limitation reads as rigor; an unnamed one reads as a defect when a reader finds it.

**Run it** — `docker-compose up`, and the indexing command. One command to a working system.

### What does not go in the README

Full API documentation, exhaustive schema listings, a decision log, or the design documents themselves. Link them; do not inline them. A long README is not read.

---

## 3. Repository metadata

Cheap, and it changes how the repository reads at a glance.

- **Description:** *"Finds the past pull requests a reviewer should see before approving a new one. Hybrid retrieval over PR history."*
- **Topics:** `information-retrieval`, `semantic-search`, `pgvector`, `sentence-transformers`, `developer-tools`, `code-review`, `github-actions`, `fastapi`
- **Pin the repository** on your GitHub profile
- **Website field** → the demo link
- `docs/demo.gif` and `docs/architecture.png` committed

---

## 4. The metric, phrased three ways

The same result, for three audiences. Substitute real figures after Phase 6; **do not ship placeholders.**

**For the README and demo page — comparative:**
> Recall@3 improves XX points over keyword search alone, measured on 300 hand-judged pairs.

A delta against a named baseline is instantly legible. A bare percentage is not — a non-specialist has no reference point, and a specialist needs a beat to place it.

**For the resume — precise:**
> XX% Recall@3 on held-out queries from a 300-judgment manually labeled evaluation set

**For conversation — plain:**
> "It surfaces a genuinely relevant past PR in the top 3 for about XX% of pull requests."

### On placeholders

Every `XX` in this document is a placeholder. **The "+18 points" figure used in earlier drafts of `05_frontend.md` was an illustrative invention, not a measurement.** Any number that reaches a resume, README, or demo page must come from `eval/score.py` output on the holdout split. Shipping an invented number would violate the project's central premise.

---

## 5. Resume entry

Format follows the placement deck: descriptive title, bullets, technologies, links.

> **PR Review Assistant** — *github.com/<user>/pr-review-assistant · live demo*
> - Built a retrieval system indexing X,XXX pull requests from the p5.js repository using hunk-level diff embeddings and hybrid search (vector similarity + BM25 + file-path overlap) with per-query score normalization
> - Achieved **XX% Recall@3 on held-out queries** from a 300-judgment manually labeled evaluation set, with a documented relevance rubric and a fully reproducible offline harness
> - Deployed as a GitHub Action that auto-comments the top 3 related past PRs on every new PR, flagging prior attempts that were closed without merging
> - **Tech:** Python, FastAPI, PostgreSQL/pgvector, sentence-transformers, Docker, GitHub Actions

**Keyword coverage** matters for ATS matching. The bullets deliberately carry: *retrieval system, embeddings, hybrid search, vector similarity, normalization, evaluation, reproducible, deployed*. Not stuffed — but "hybrid search" alone matches fewer postings than the fuller vocabulary.

### The one sentence for interviews

> "I built a retrieval system that indexes a GitHub repo's PR history using hunk-level embeddings and hybrid search, automatically surfaces the top 3 related past PRs when a new one opens, and achieves XX% Recall@3 on a manually labeled held-out evaluation set."

Method, mechanism, deployment, number. Complete in one breath.

---

## 6. Outreach framing

For LinkedIn referral requests (the placement deck's 40–50 customized messages), the project supplies two or three sentences — not a paragraph.

**What to lead with depends on the company:**

- **Atlassian and developer-tool companies:** lead with the domain. Bitbucket occupies this exact problem space.
- **MAANG and general product companies:** lead with the measurement. *"I built and evaluated a retrieval system"* separates you from *"I built a project."*

**What not to do:** send the full technical description. The referral message's job is to earn a profile click, not to explain the architecture.

---

## 7. Anticipated questions

The README should preempt these; the answers live across the design docs.

| Question | Answer lives in |
|---|---|
| Why hunk-level chunking? | `03` §2 |
| Why sentence-transformers over an API model? | `03` §3 |
| Why pgvector over a managed vector database? | `02` §1 |
| Why three signals instead of vectors alone? | `03` §1, with the baseline table as evidence |
| Why Recall@3 and not precision@3? | `01` §11 — **the strongest technical story the project produces** |
| Why normalize per query? | `03` §8 |
| What happens at 10,000 PRs? | `02` §5 |
| Why one service instead of two? | `04` §1 |
| Why is the demo page hosted separately from the API? | `04` §1, `05` §5 |
| What happens if the API is down? | `05` §6 — the page still shows real results |

The precision@3 story deserves rehearsing until it is fluent. It demonstrates that a metric was chosen rather than inherited — and that is a rarer signal than any number.

### A second story worth having ready

**"My deployment target started charging mid-build."** Hugging Face began requiring a paid plan for Docker Spaces in July 2026, invalidating a locked decision on day 1.

The answer is not that you found another host. It is that **the architecture absorbed it**: the evaluation harness was already deployment-independent, so no published number moved, and the demo page was already designed to render from precomputed results, so the recruiter-facing path never touched a live service at all. The migration was doc edits and a Dockerfile change.

That is a story about designing for the things you do not control — and it is more interesting than "I deployed to X."*

---

## 8. Checklist

- [ ] GIF recorded during Phase 7 and placed above the fold
- [ ] Demo link in the first screen and in the repository's website field
- [ ] Comparative metric above the fold
- [ ] Baseline comparison table included in the evaluation section
- [ ] Rubric linked from the README
- [ ] Limitations section present
- [ ] Architecture diagram committed
- [ ] `docker-compose up` verified from a clean clone
- [ ] Topics and description set; repository pinned
- [ ] **No placeholder numbers anywhere** — every figure traces to `eval/score.py` on the holdout split
- [ ] Resume bullets written and cross-checked against `00_problem_statement.md` §7 criterion 3 — every claim defensible for twenty minutes
