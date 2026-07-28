# PR Review Assistant — Demo Frontend

**v1.3 — Locked July 2026**

*Changed from v1.2: the page moves to a static host, separate from the API (`04_architecture.md` §1). Keepalive removed; the waking state is now custom-query-only.*
*Changed from v1.1: §3 adds the sketch-before-build requirement for the contribution bar.*
*Changed from v1.0: added §5 (seeded results) to remove cold start from the critical path; §8 (shareability); metric strip is now comparative; purpose sharpened around screen-stage impact.*

One page. Its job is to make the retrieval engine visible and credible to someone who will not install a GitHub Action.

Depends on `04_architecture.md` §4 (`GET /similar/{owner}/{repo}/{pr_number}`).

---

## 1. Purpose

Two audiences, in priority order:

1. **A recruiter or interviewer with 30 seconds.** They open the repo, click the demo link, and must immediately see: this is real, it runs on a real repository, and it produces a measured result.
2. **A developer evaluating the tool.** They want to judge whether the retrieved PRs are actually relevant.

**The page's single job:** prove the hybrid retrieval works on real data, and make *why* each result ranked where it did legible at a glance.

**The page has roughly 30 seconds and must not spend any of them loading.** This constraint drives §5 and outranks every other consideration in this document. A demo that is perfect after sixty seconds has already failed.

This is not an admin panel. There is no repo management, no indexing controls, no settings — those were cut deliberately (`04_architecture.md` §2) and adding UI for them would reintroduce scope.

---

## 2. Scope

**In:** one page. Seeded example results, query input, three results, per-result score breakdown, a project header carrying the evaluation number.

**Out:** authentication, multi-repo selection, indexing UI, history, saved queries, dark-mode toggle.

---

## 3. Design direction

### Grounding

The subject's world is code review: diffs, hunks, `@@` markers, PR numbers, merge states. The vernacular is monospaced identifiers and `+`/`-` gutters. The design draws from that vocabulary — but **green and red are reserved strictly for diff semantics** and never used as interface chrome, because in this context they already mean *added* and *removed*.

The product is about **memory** — surfacing what the repository already knows. The page reads as an archive lookup, not a search engine.

### Color

Six named values. Three are functional: each signal owns a colour, and that mapping holds everywhere it appears.

```css
--ink:          #14161F;  /* blue-shifted near-black — body text, headings */
--paper:        #F7F6F3;  /* cool off-white — page background */
--slate:        #5B6172;  /* secondary text, metadata, labels */
--signal-vec:   #4C6EF5;  /* indigo  — vector similarity */
--signal-file:  #12B886;  /* teal    — file-path overlap */
--signal-bm25:  #F59F00;  /* amber   — BM25 */
--flag:         #E8590C;  /* rust    — "closed without merging" only */
```

`--flag` is used in exactly one place. Spending a distinct colour on the closed-unmerged badge is deliberate: it is the highest-value signal the tool produces, and it should be where the eye lands.

### Type

| Role | Face | Use |
|---|---|---|
| Display | **Bricolage Grotesque** | Page title and result titles only. Used with restraint. |
| Body | **IBM Plex Sans** | Prose, labels, reasons |
| Data | **IBM Plex Mono** | PR numbers, file paths, scores, identifiers |

The mono face is not decorative — it carries every value a developer would compare digit-by-digit. Plex Sans and Plex Mono share a design origin, so the pairing holds together while Bricolage supplies the character.

Type scale: `12 / 14 / 16 / 20 / 32 / 48`.

**Subset aggressively.** Load only the weights used — display 700, body 400/500, mono 400. Three families unsubsetted would be 150–250KB against a 30KB page, dominating load entirely. `font-display: swap` with a system fallback stack so a slow font fetch never blocks first paint.

### Signature element — the contribution bar

**The one thing this page is remembered by.**

Under each result, a horizontal stacked bar shows how much each signal contributed to the final score, segment widths proportional to `weight × normalized_score`:

```
┌──────────────────────────────────────────────┐
│████████████████│██████████████│██████        │  0.71
└──────────────────────────────────────────────┘
 vector 0.34      file 0.30      bm25 0.07
```

**Why this and not a score badge.** The project's entire technical claim is that three signals combine to beat any one of them. A single number hides that; the bar *is* the argument, rendered. It also makes a genuinely interesting case visible: a result ranking high on file overlap but low on vector similarity looks obviously different from one high on both, and a viewer sees that without reading anything.

Hovering a segment reveals the raw and normalized values for that signal.

**Sketch it with fake data before Phase 8 builds it.** On a prior project the named hero component was built, its data layer fully verified, and then rejected on aesthetics — after which it was deferred twice and never shipped in its intended form. The contribution bar carries the same risk: it is specified in text and has never been seen. One hour, any tool, during a Phase 5 labeling break (`09_timeline_and_milestones.md` §4, Milestone B′; `11_workflow.md` §9).

### Layout

Single column, max width 720px, generous vertical rhythm. No sidebar, no grid — the content is a short ranked list and a column is the honest shape for it.

```
┌────────────────────────────────────────────┐
│  PR Review Assistant                       │  display, 48
│  Finds the past pull requests a reviewer   │  body, 16, --slate
│  should see before approving this one.     │
│                                            │
│  +XX pts over keyword search · 300 judged  │  mono, 12
├────────────────────────────────────────────┤
│  [ paste a processing/p5.js PR URL   ] [→] │
│  showing  #16024 ·  #15975   #15515        │  mono links
├────────────────────────────────────────────┤
│  ┌──────────────────────────────────────┐  │
│  │ #15992  closed without merging       │  │  ← --flag badge
│  │ fix: pass include/exclude/by_alias…  │  │  display, 20
│  │ ████████│██████│███         0.71     │  │  ← signature
│  │ Both modify fastapi/encoders.py      │  │  body, --slate
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │ #15641  merged                       │  │
│  └──────────────────────────────────────┘  │
└────────────────────────────────────────────┘
```

### Motion

One orchestrated moment, nothing scattered: results stagger in at 60ms intervals and each contribution bar animates its segments from zero to width over 400ms. That single sequence makes the scoring feel computed rather than fetched.

Everything else is static. Hover states are instant.

---

## 5. Seeded results

**The most important behavioural decision on this page.**

The three example queries have their results **precomputed and shipped with the page** as static JSON. On load, the page renders them immediately — no network round trip, no spinner, no cold start.

The live service is called **only** when a visitor submits their own PR URL.

### Why

Cloud Run scales to zero, and a cold start with torch and MiniLM loaded is an unmeasured cost somewhere between fifteen and sixty seconds (`04_architecture.md` §7). Under a live-first design, a recruiter's very first click produces a blank page for that whole duration — and they conclude the demo is broken.

Seeding removes cold start from the critical path entirely. **The default experience is instant.**

**The page is also hosted separately from the API** (`04_architecture.md` §1). It is static files on a static host; the API is a JSON service on Cloud Run. That makes the guarantee structural rather than best-effort: the page cannot be slowed by a service that is scaled to zero, because on the default path it never contacts one.

### Honesty

These are **real outputs from the real system**, computed by the same pipeline with the same locked weights — just computed ahead of time rather than on click. Nothing is fabricated or hand-picked for flattery, and the examples are not chosen to hide weak cases.

The seed file records provenance:

```json
{
  "generated_at": "2026-09-12T14:03:00Z",
  "weights": { "vector": 0.5, "file": 0.3, "bm25": 0.2 },
  "model": "all-MiniLM-L6-v2",
  "queries": { "16024": [ /* three results */ ] }
}
```

### Regeneration

`scripts/generate_seeds.py` re-runs the three queries and writes `frontend/seed_results.json`. **Run it after weights are locked, and again on any re-index.** Stale seeds that disagree with the live service are worse than no seeds — the page logs a console warning in development when the seed `weights` do not match the service's current constants.

### No keepalive

Version 1.2 specified a scheduled ping to keep a sleeping container warm. **Removed.**

Under the split architecture the demo page never touches compute, so there is nothing to keep warm for it. Pinging Cloud Run on a schedule would burn free-tier vCPU-seconds to shorten a cold start that only affects custom queries — a cost paid continuously for an occasional benefit.

Seeding is the fix, and it is sufficient on its own.

---

## 6. States

Five. With seeding in place, the default path touches only the first.

| State | Treatment |
|---|---|
| **Seeded (default)** | Three real results rendered on load from static JSON. No spinner, no fetch. This is what a recruiter sees. |
| **Loading** | Skeleton cards matching final layout. Custom queries only. |
| **Waking** | **Custom queries only** — never on the default path. After 3 seconds: *"Starting the retrieval service — this takes a moment after it's been idle."* Honest and specific; prevents a visitor concluding the demo is broken. |
| **No results** | *"No past pull requests scored above the threshold. This one looks new to the repository."* — a real finding, framed as one. |
| **Error** | *"Couldn't reach the retrieval service. Showing the cached examples instead."* — **falls back to the seeded results rather than an empty page.** The demo degrades to working, never to broken. |

That error behaviour matters, and under the split architecture it is **structurally true rather than hopeful**: the page and the API are separately hosted, so the API can be down, misconfigured, or over quota and the page still loads and still shows real results.

---

## 7. Components and copy

| Component | Contents |
|---|---|
| `PageHeader` | Title, one-line description, metric strip |
| `QueryInput` | URL field, submit, three example PR links |
| `ResultCard` | PR number, outcome badge, title, contribution bar, reason string |
| `ContributionBar` | Three segments, final score, hover detail |
| `OutcomeBadge` | `merged` / `closed without merging` / `open` |
| `StateMessage` | Loading, waking, no-results, error |

`OutcomeBadge` copy is fixed by `03_retrieval_engine.md` §10: **never "rejected."**

### Copy

Plain, active, specific. Written from the reader's side of the screen.

- **Header description:** *"Finds the past pull requests a reviewer should see before approving this one."* — what it does, not what it is built from.
- **Submit control:** **Find similar PRs**, not *Submit*.
- **Metric strip — comparative, not absolute:**

  > *"+XX pts Recall@3 over keyword search · 300 hand-judged pairs · processing/p5.js"*

  An absolute percentage means little to a non-specialist and takes a specialist a beat too long to place. A **delta over a named baseline** is instantly legible to both. The baseline numbers come free — the harness already scores each signal individually (`03_retrieval_engine.md` §1). Substitute the real figures once the holdout run is complete.

- **Signal labels:** **vector**, **file overlap**, **terminology** — the third is the reader-facing name for BM25, which means nothing to a non-specialist. A label's job is to be understood.

---

## 8. Shareability

The page will be linked from a resume, a LinkedIn post, and a README. It must render correctly as a link preview.

```html
<title>PR Review Assistant — finds related past pull requests</title>
<meta name="description" content="Surfaces the past pull requests a reviewer should see before approving a new one.  Hybrid retrieval over X,XXX p5.js PRs.">
<meta property="og:image" content="/static/preview.png">
<meta name="twitter:card" content="summary_large_image">
```

`preview.png` is a 1200×630 static image showing the results view with the contribution bars visible. It is generated once by screenshotting the seeded state — no runtime dependency.

Cheap, and it is the difference between a shared link that shows the tool and one that shows a grey placeholder.

---

## 9. Technology

**Single static HTML file with vanilla CSS and JavaScript, deployed to a static host.** `seed_results.json` ships alongside it.

Any static host works — GitHub Pages, Cloudflare Pages, Netlify, or a Hugging Face Static Space (still free). The page has no build step and no server-side dependency, so the choice is reversible in minutes.

The API is called cross-origin, so `04_architecture.md` §8's CORS rule applies: the service allows this host's origin specifically, never `*`.

**Rationale.** The page is one screen with one optional fetch and five states. React would add a Node toolchain, a bundler, and a build stage inside the Docker image to render a list of three cards — real deployment surface added during days 43–47, the wrong week to debug a build pipeline.

**Tradeoff, stated honestly:** this forgoes a React line on the resume. Given that the project's signal is retrieval quality and measurement rigour — and that the frontend's job is to *demonstrate* those, not to be the achievement — the simpler path is correct. The page is small enough to port to React in an afternoon if wanted later.

Expected size: roughly 650 lines, ~30KB unminified, excluding fonts.

---

## 10. Quality floor

Not announced, just met:

- Responsive to 360px — cards stack, contribution bar stays legible
- Visible keyboard focus on input, submit, and example links
- `prefers-reduced-motion` respected — stagger and bar animation disabled
- Contribution bar segments carry text labels, so the three signal colours are never the sole carrier of meaning
- Semantic HTML: real `<button>`, real `<form>`, proper heading order
- Fonts subsetted; total page weight under 100KB including fonts

---

## 11. Decisions removed

| Removed | Reason |
|---|---|
| React admin UI (blueprint, ~10% scope) | Repo management, indexing controls, and settings all describe operations that moved local (`04_architecture.md` §2) |
| Live-first loading | Puts a cold start on the critical path for the highest-priority audience (§5) |
| Multi-page app with routing | One fetch, one result set. Routing would be scaffolding around a single screen. |
| Dark mode toggle | A preference control, not a demonstration |
| Green/red as interface accent colours | Reserved for diff semantics; using them as chrome would be actively confusing in this domain |
| Absolute-only metric ("Recall@3 64%") | Not legible at a glance to either audience (§7) |

---

## 12. Checklist

- [ ] Seeded results render on load with zero network calls
- [ ] `seed_results.json` records `generated_at`, `weights`, and `model`
- [ ] Seeds regenerated after weights are locked and after any re-index
- [ ] Error state falls back to seeded results, never to an empty page
- [ ] Deployed to a static host, separate from the API
- [ ] API origin allowed in CORS; page origin is configuration, not hardcoded
- [ ] Metric strip is comparative and above the fold
- [ ] OG tags present; `preview.png` generated from the seeded state
- [ ] **Contribution bar sketched with fake data before Phase 8**
- [ ] Contribution bar widths equal `weight × normalized_score`
- [ ] Signal colours consistent across bar, hover detail, and labels
- [ ] `--flag` used only on the closed-unmerged badge
- [ ] Outcome badge never reads "rejected"
- [ ] Fonts subsetted to used weights only
- [ ] Keyboard focus visible on every interactive element
- [ ] `prefers-reduced-motion` honoured
- [ ] Legible at 360px
- [ ] No build step
