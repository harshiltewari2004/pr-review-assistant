# PR Review Assistant — Evaluation Protocol

**v1.1 — Locked July 2026**

*Changed from v1.0: §14 adds predict-before-running.*

This document defines how retrieval quality is measured. It is written **before** any retrieval code, because it defines what "done" means. Every number that appears on a resume, in the README, or in an interview comes from this protocol.

---

## 1. What this measures — and what it does not

There is no objective ground truth for "are these two pull requests similar." It is a human judgment on a fuzzy concept. This protocol therefore does **not** claim to measure correctness. It measures **agreement with a documented, reproducible standard of judgment.**

What is achievable:

| Achievable | Not achievable |
|---|---|
| **Reproducible** — rubric + published labels; anyone can re-run and get the same number | An objectively "true" similarity label |
| **Unbiased** — blind labeling, so ranking does not influence judgment | Certainty that the labels are "right" |
| **Bounded** — uncertainty is stated, not hidden | A number without error bars |

A flatly stated number with no caveats is a weaker result than a lower number reported with its confidence interval and self-agreement rate. This protocol optimizes for the second.

---

## 2. Corpus definition

The indexed corpus is **code-change pull requests only**. The following are excluded at ingest time:

| Excluded | Filter | Why |
|---|---|---|
| Bot PRs | `author_type = 'Bot'`, plus an explicit account list: `p5js-bot`, `github-actions`, `allcontributors`, `dependabot` | Near-identical dependency bumps and regenerated contributor tables match each other at ~0.99 and mean nothing |
| Maintainer housekeeping | title matches `chore: update contributors.png`, `chore: update README table from stewards.yml`, or `(update\|Update) stewards.yml` | Recurring automation noise; human-authored, so the bot rule misses it |
| Duplicate resubmissions | same author **and** near-identical title **and** within 7 days — keep the merged one, else the highest PR number; exclude the rest | The same diff submitted two or three times after a botched branch. Trivially perfect self-matches that would dominate retrieval while demonstrating nothing |

**Two rules from the FastAPI-era corpus have no counterpart here and are deliberately absent:**

- **No `lang-*` rule.** p5.js has no per-language label. Translations are human-authored PRs against `translations/{locale}/translation.json` (i18next), invisible to every metadata rule. They are excluded on content instead: the locale payloads are dropped at chunk level (`03_retrieval_engine.md` §2) and the resulting zero-hunk PR is marked out of corpus at step 4b (`D-P2-3`).
- **No `release` rule.** p5.js's release process has not been characterised. Absent evidence, no row — an unevidenced filter is worse than a missing one, because it excludes silently and the count in the README would be unexplainable.

**Rationale.** These categories are trivially self-similar. Including them would inflate any metric while demonstrating nothing — a filename match would score well on them. Excluding them is also a better product: surfacing "here is another auto-generated commit" wastes a reviewer's time. The tool is for code changes where prior context matters.

**On duplicate resubmissions — and why they are not §6 rule 4.** Observed in p5.js: `#8947`/`#8946`/`#8945` (identical title, three times), `#8842`/`#8841`, `#8846`/`#8844`, `#8837`/`#8845`. Same author, same day, same change.

This looks like §6 rule 4 — *"a superseded or abandoned attempt at the same change is a grade 2"* — and it is the opposite. Rule 4 exists for `#8829` ↔ `#8933`: **two different solutions** to one problem, where the abandoned approach teaches the reviewer something. A resubmission is **the same solution twice**, usually after a force-push or a branch mistake. It teaches nothing and would score ~1.0 on every signal simultaneously.

Excluding these protects rule 4 rather than contradicting it. If resubmissions stayed in the corpus, the highest-value retrieval case in the system would be indistinguishable from its most trivial one.

**The table above is metadata-only by construction.** `04_architecture.md` §5 applies these rules at step 2, *before* diffs are fetched at step 3 — the ordering that avoids ~5,000 wasted requests. A duplicate rule that compared diffs would invert that and cost a rate-limit window. Author + title + time window is what is available at step 2, and it is enough.

**One further exclusion is content-based and runs later.** A PR whose diff yields zero hunks after `03_retrieval_engine.md` §2's file exclusions is marked `in_corpus = FALSE`, `exclusion_reason = 'no_source_content'`, at `04_architecture.md` §5 step 4b. It costs no extra requests — the diff is already fetched and parsed — and it catches the categories no metadata rule can see: translation-only PRs, and docs-only PRs in a repository where `Documentation` is a facet rather than a type. That is why this table has no `lang-*` row and no documentation row at all: on `processing/p5.js` a `Documentation` label sits alongside `Area:*` and `Enhancement` on mixed PRs, so a label rule would strip real code changes — heaviest in the p5.strands cluster, one of the two densest. Content is the only reliable test.

False positives are cheap in both stages: exclusions are marks, not deletions (`02_data_models.md` §4), so a wrongly-excluded PR is one `UPDATE` away from returning.

**Repository:** `processing/p5.js`. Approximately 4,175 closed PRs — the same order of magnitude as the FastAPI corpus originally specified, so no estimate elsewhere in the document set changes materially.

Selected on four grounds, each checked rather than assumed:

1. **Dense clustering of genuine code-change work.** Seven subsystems carry observed multi-PR clusters (§8) — the Friendly Error System, p5.strands transpilation, WebGL shaders, Vector/Math, image and colour, framebuffer/renderer, and output. `Area:*` labels make the stratification machine-readable rather than hand-assigned.
2. **A healthy merged / closed-unmerged mix.** Both outcomes are well represented in the recent window — merged: `#8829`, `#8823`, `#8862`, `#8964`, `#8912`, `#8917`; closed unmerged: `#8933`, `#8833`, `#8842`, `#8841`, `#8846`, `#8844`, `#8954`. The closed-without-merging flag — the highest-value output in the system (`00_problem_statement.md` §2) — has real data behind it.
3. **Readability for the human labeler.** JavaScript, in a repository the labeler actively contributes to. Domain familiarity raises label quality, which is the binding constraint on every number this protocol produces.
4. **Measured, not assumed, vector performance.** The Day-4 embedding spike recorded a similar-minus-control separation of **+0.3394** on p5.js against **+0.1882** on FastAPI, both inside `09_timeline_and_milestones.md` §5's *">0.15 — vector signal discriminates"* band. The FastAPI control was the worse size-matched of the two, which inflates FastAPI's figure — so the honest reading is that **the embedding arm is a wash, not a p5.js win.** Ground 3, not ground 4, is what decided it (`D-P1-2`).

**The cost of ground 3, stated here because it is a real one.** A labeler who authored some of the candidate PRs cannot label those pairs blind, and §10's blind requirement is structural, not a matter of discipline. See `D-P5-1`.
---

## 3. Relevance definition — the core test

Every judgment answers one question, in this exact form:

> **If the reviewer of PR A had not seen PR B, would their review be worse — and can you name the specific way?**

The second clause is what converts intuition into a judgment. A vague positive feeling about a pair is not relevance. If you cannot finish the sentence *"without B, the reviewer would ___"*, it is not a grade 2.

There are exactly three valid completions:

1. **…miss a known failure mode** that B already surfaced
2. **…re-litigate a design debate** that B already settled
3. **…duplicate work** that B already did, or already attempted and abandoned

**Why utility, not structure.** Three alternative definitions were considered and rejected:

- *Structural* (same files touched) — circular. The file-overlap signal would score near-perfectly by construction, making the evaluation meaningless.
- *Root cause* (same underlying bug) — too narrow. Would yield too few positives per query to measure anything.
- *Approach* (same technique) — inconsistently judgeable without deep reading of every diff.

Utility is harder to label consistently, which is precisely why §8 and §11 exist. It is chosen because it is the only definition that matches what the product claims to do. The tool's pitch is *"reviewers are reviewing blind; this gives them memory."* If the metric measured file overlap, it would measure something the product does not claim. Utility makes the metric and the product claim the same statement.

---

## 4. Grades

| Grade | Meaning | Test |
|---|---|---|
| **2 — Strongly related** | The reviewer should see this before approving | Passes §3 with a nameable consequence |
| **1 — Related** | Useful background; would not change the decision | Same subsystem or concern, no specific nameable consequence |
| **0 — Unrelated** | Costs the reviewer time for nothing | Different subsystem, no meaningful connection |

**Three grades, not five.** A solo labeler cannot hold five levels consistent across 300 judgments. The additional granularity would be immediately lost to labeling noise, and noise is bias — which no amount of extra data corrects.

---

## 5. The temporal constraint

**Candidates must predate the query PR.** Hard filter, enforced in code:

```
candidate.created_at < query.created_at
```

The product surfaces *past* PRs. If evaluation permits a PR created three months later to count as relevant, the system is credited for retrieving something it could never have had at inference time. This is temporal leakage and it silently inflates every reported number.

**This filter lives in the pooling script, not in labeler discipline.** It will be forgotten otherwise.

**Corollary:** query PRs are drawn from the recent end of the repository, so each has a large legitimate history behind it.

---

## 6. Edge-case rules

These are the calls that would otherwise drift across a multi-hour labeling session.

1. **Same file is not sufficient for a grade 2.** `fastapi/encoders.py` is touched by dozens of unrelated PRs. Same *function* or same *behavior* earns a 2. — *Without this rule, the file-overlap signal scores ~100% by construction and the evaluation becomes circular. This is the single most important rule in the document.*
2. **Different file is not disqualifying.** A bug fixed in `responses.py` in one PR and `routing.py` in another can be a grade 2. This is exactly the case vector similarity exists to catch and file overlap misses.
3. **Trivial changes to a shared file are grade 0, not 1.** A docstring typo fix in `encoders.py` is unrelated to a real encoder change.
4. **A superseded or abandoned attempt at the same change is a grade 2.** This is the highest-value retrieval case in the entire system.
5. **Test-only PRs grade against the code they test**, by the same rules.
6. **Cluster labels are not judgments.** Some PRs span two clusters — e.g. `#15708`, "Fix response model serialization options for SSE event data," is both an encoder change and an SSE change. Judge the specific behavior changed against the query, not the cluster the PR appears to belong to. §7's grade-0 anchor assumes the clusters are disjoint; they are not.
---

## 7. Worked anchors
> **STALE — FastAPI-era, pending rewrite (`D-P5-2`).** The anchors below were verified against `fastapi/fastapi` and predate the corpus change to `processing/p5.js` (§2). They still illustrate the *reasoning*, which is why they are kept rather than deleted, but they are not consultable examples for a p5.js judgment. Rewrite before Day 25. One p5.js grade-2 anchor is verified and ready — `#8829 ↔ #8933`, two solutions to the same static-`Vector`-method problem, one superseded (§6 rule 4), different files so Jaccard is 0.0 and the vector signal carries it alone.
These examples are part of the rubric. Consult them when a judgment feels ambiguous.

**Grade 2**
- **#15994 ↔ #15992** — both pass `include`/`exclude` params to `jsonable_encoder`, same author, same week. *Without B: reviewer duplicates a review already performed.*
- **#15937 ↔ #15813** — both modify the JSONL `StreamingResponse` construction in `fastapi/routing.py`. #15937 replaces the exact `background=...` line that #15813 modifies, so the two conflict. *Without B: reviewer misses an interaction.*
**Grade 1**
- **#15641 (jsonable_encoder UTF-8 crash) ↔ #15476 (jsonable_encoder set-allocation perf)** — same file, genuinely different concerns. Useful context; would not change the decision.
- **#16024 (Form with Optional Pydantic model) ↔ #16030 (Pydantic Header field alias)** — both Pydantic field handling, different entry points.

**Grade 0**
- Anything in the `jsonable_encoder` cluster paired with anything in the router or SSE clusters.

---

## 8. Query selection

**20 query PRs**, drawn from genuine code-change clusters.

**Stratification is mandatory.** Queries must span at least six distinct subsystems — for example: `jsonable_encoder`, SSE / streaming, router internals and caching, OpenAPI generation, Pydantic / Form handling, dependency injection.

> **The subsystem list above is FastAPI-era (`D-P5-2`).** p5.js supplies seven observed clusters against §8's ≥6 requirement — Friendly Error System, p5.strands transpilation, WebGL shaders, Vector/Math, image and colour, framebuffer/renderer, output — and `Area:*` labels make the stratification machine-readable rather than hand-assigned. Rewrite with PR lists before Day 25.

Twenty queries concentrated in three clusters is a **worse** evaluation than twelve spread across eight. The metric measures generalization, not performance on one neighborhood.

**Why 20.** Query count drives the confidence interval, narrowing roughly as `1/√n`. Moving from 15 to 20 narrows it by about 13%; 15 to 30 by about 29%, at double the labeling hours and materially worse label quality by hour six. Beyond roughly 25 queries the marginal return does not justify the fatigue cost. Twenty is the stopping point.

---

## 9. Pooling procedure

Relevance is judged **after** retrieval, not before. Pre-labeling a fixed set of pairs is invalid: the system's top-3 will contain PRs that were never labeled, leaving them unjudged and unscoreable.

**Procedure, per query PR:**

1. Run four retrieval variants: vector-only, BM25-only, file-overlap-only, and hybrid at two weight settings.
2. Take the **top 6** from each.
3. Apply the temporal filter (§5).
4. Union and deduplicate → approximately **15 unique candidates**.
5. Judge every item in the pool. Nothing is left unjudged.

**Total: 20 queries × ~15 candidates ≈ 300 judgments.**

**Why pool across multiple variants.** Pooling only from the final hybrid system biases the labels toward it, and re-tuning weights would immediately surface unjudged items — putting you back in the invalid state. Pooling across variants means almost any later weight setting is already covered. This is standard TREC-style IR evaluation methodology.

---

## 10. Labeling protocol

- **Blind.** Shuffle the pool before judging. Strip rank and source variant. Without this, top-ranked items are unconsciously rated more similar (anchoring) and the metric quietly grades itself.
- **Time-boxed.** ~45 seconds per judgment. Deep-diving some pairs while skimming others is a silent bias source.
- **Reason string required for every grade 1 and 2.** Six words or fewer. Forces the §3 test, doubles as README and interview material. If you cannot write the reason, downgrade.
- **Skip is allowed, capped at 5%.** Track the rate. Exceeding it means query selection has outrun your reading comfort — fix the queries, not the rubric.
- **One sitting per batch**, so calibration does not drift mid-set.

**Staged execution:**

1. Label batch 1 (10 queries, ~150 judgments).
2. Run the self-agreement check (§12).
3. Revise the rubric if agreement is poor.
4. Label batch 2 (10 queries, ~150 judgments).

Discovering an ambiguous rubric after 150 judgments is recoverable. After 300 it is not.

---

## 11. Metrics

**Primary — Recall@3**

> Of the relevant past PRs for a query, what fraction appear in the top 3?

Reported at two thresholds:

- **Strict Recall@3** — grade 2 only. **This is the headline number.**
- **Lenient Recall@3** — grades 1 and 2.

Reporting both demonstrates that the result's sensitivity to a subjective threshold is understood. A single number pretends the threshold does not exist.

**Secondary — MRR.** Reciprocal rank of the first relevant result, averaged across queries. Rewards ranking quality and has no ceiling.

**Known limitation, stated openly:** Recall@3 is capped at `3/|relevant|` when a query has more than three relevant PRs. Observed clusters in this repository appear to run 2–5, based on subsystem grouping during query selection; the FES and p5.strands clusters are the largest. The precise distribution is not known until labeling completes, which is why `|relevant|` per query is published rather than asserted (§14 item 5).

**Pooled recall, not absolute recall.** The relevant set is what the pool surfaced, not exhaustive ground truth over all ~6,000 PRs. This is standard IR practice and is stated explicitly in the README.

### Why precision@3 was rejected

The original project blueprint specified precision@3 with a target near 74%. This was removed.

**Precision@3 is capped at `min(1, |relevant| / 3)`.** A query with two genuinely similar PRs in the entire repository has a maximum possible precision@3 of **67% — with a perfect system**. A query with one caps at **33%**.

Since observed clusters run roughly 2–5 PRs, a 74% precision@3 on genuine clusters is arithmetically impossible. Such a number could only arise from trivial matches — translation PRs, dependency bumps — which the metadata rules in §2 and the zero-hunk filter at `04_architecture.md` §5 step 4b exist to exclude.

*This section is retained deliberately. The reasoning behind the metric switch is one of the strongest technical signals the project produces, and future readers should not have to rediscover it.*

---

## 12. Label verification

Applied in order.

**1. Rubric before labeling.** This document is committed to the repository before the first judgment. Ambiguity is what makes labels noisy; a written rubric with worked anchors is what makes them reproducible.

**2. Blind labeling.** See §10.

**3. Self-agreement re-test.** One week after labeling, re-judge ~50 items **without consulting the original labels**. Compute **quadratic weighted kappa** — the correct statistic for an ordinal 3-point scale.

**The sample is stratified, not random.** Every pair flagged `self_authored` enters the re-test; the remainder is drawn at random to reach ~50. Kappa is computed twice — over the full sample, and over the self-authored subset alone. This is the only mechanism that turns `D-P5-1`'s familiarity bias into a measurement rather than a caveat, and a random sample would not supply enough of the subset to compute one.

**If the self-authored subset is under ten pairs, report its size and state that it cannot support a kappa.** Publishing a statistic that `n` cannot carry is the same error as publishing a bare percentage (§14).

This is the highest-value verification available. It costs roughly 40 minutes and produces a defensible statement about labeling reliability that almost no comparable project has. If self-agreement is 70%, no metric built on these labels can be trusted beyond that ceiling — and saying so is a strength, not a weakness.

**4. Second annotator (optional).** A second reader labels 20–30 of the same items; compute Cohen's kappa. Upgrades the ground truth from one person's opinion to a measured judgment.

---

## 13. Tune / holdout split

**Split by query, never by judgment** — judgments from one query would otherwise leak across the split.

- 20 queries → **10 tune / 10 holdout**
- Hybrid weights are tuned **only** on the tune set
- The holdout set is not examined until weights are locked
- **Both numbers are reported**

Example: *"Strict Recall@3: 71% tune, 64% holdout."* The gap is the overfitting, stated openly. Ten holdout queries is a small sample; that is stated too. Small and honest survives questioning. Large and fabricated does not.

---

## 14. Reporting format

Every published result includes:

1. Strict and lenient Recall@3, tune and holdout
2. MRR
3. **Bootstrap 95% confidence interval** — resample queries with replacement, 1,000 iterations, percentile interval. Expect roughly ±8–12 points at n=10.
4. Self-agreement (quadratic weighted kappa) and the size of the re-test sample
5. Distribution of `|relevant|` per query
6. Corpus size after filtering, and the filters applied

**README line:**

> Strict Recall@3: X% (95% CI: X–Y) on 10 held-out queries from `processing/p5.js`, over 300 manually judged candidates. Labeler self-agreement: κ = Z.

**Never** report a bare percentage. The interval and the self-agreement rate are what make the number credible.

### Predict before running

**Before executing the harness, write down the Recall@3 you expect.** Same for retrieval on a known query: name the PR you expect back before you run it.

A result that surprises you is either a bug or a finding, and **you cannot tell which if you had no expectation.** On a prior project this ritual held for five phases and then eroded under time pressure at exactly the point the numbers became the deliverable (`11_workflow.md` §7). Phase 6 here is that point.

Record the prediction in `JOURNAL.md` alongside the actual. The gap between them is the most useful thing in the file.

---

## 15. Reproducibility

The evaluation harness is **offline and deployment-independent**. It runs locally against a frozen snapshot of the indexed corpus and never contacts the deployed service.

**Why:** the harness is re-run dozens of times during weight tuning. Deployed state drifts as the service restarts or re-indexes; cold starts and network variance inject noise into a measurement that must be deterministic.

**Committed to the repository:**

- This document
- `judgments.jsonl` — every judgment with query ID, candidate ID, grade, and reason string
- `queries.json` — the 20 query PRs and their tune/holdout assignment
- `eval.py` — one command, reproduces every published number
- `corpus_snapshot.json` — the filtered PR set and its ingest timestamp

---

## 16. Checklist

Before any number is published:

- [ ] Corpus filters applied and documented
- [ ] Temporal filter enforced in the pooling script
- [ ] 20 queries selected, stratified across ≥6 subsystems
- [ ] Pool built from 4 variants, deduplicated
- [ ] Batch 1 labeled blind, self-agreement check run, rubric revised if needed
- [ ] Batch 2 labeled blind
- [ ] Skip rate under 5%
- [ ] Weights tuned on tune split only
- [ ] Holdout evaluated exactly once
- [ ] Bootstrap CI computed
- [ ] Quadratic weighted kappa computed
- [ ] All artifacts in §15 committed
