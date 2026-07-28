# PR Review Assistant — Architecture

**v1.2 — Locked July 2026**

*Changed from v1.1: deployment retargeted from Hugging Face Spaces to Google Cloud Run — HF began requiring a paid plan for Docker Spaces in July 2026. The frontend leaves the service and moves to a static host. §1, §4, §7, §8, §9 revised.*
*Changed from v1.0: §5 adds a raw API response cache before parsing (`11_workflow.md` §6); §3 adds `.cache/` and the three record-keeping files.*

One Python service, one Postgres database, one GitHub Action. Defines the runtime shape, the offline indexing pipeline, and how the pieces authenticate to each other.

Depends on `02_data_models.md` and `03_retrieval_engine.md`.

---

## 1. System shape

```
   ┌─────────────────────┐
   │  Local machine      │   scripts/index_repo.py
   │  (indexing only)    │   GitHub API → chunk → embed → write
   └──────────┬──────────┘
              │ writes
              ▼
   ┌─────────────────────┐
   │  Neon Postgres      │   pull_requests · chunks(vector) · judgments
   │  + pgvector         │
   └──────────┬──────────┘
              │ reads
              ▼
   ┌─────────────────────┐        ┌──────────────────────┐
   │  FastAPI service    │◄───────│  GitHub Action       │
   │  (Cloud Run, →0)    │  JSON  │  on: pull_request    │
   └──────────┬──────────┘        └──────────┬───────────┘
              │ CORS — custom queries only   │ posts comment
              ▼                              ▼
   ┌─────────────────────┐        ┌──────────────────────┐
   │  Static host        │        │  GitHub PR thread    │
   │  seeded results     │        └──────────────────────┘
   └─────────────────────┘
```

### The frontend is not served by the service

**This is the one structural change from v1.1.** The demo page lives on a static host; Cloud Run serves JSON only.

This is not a concession to the platform — it is what `05_frontend.md` §5 already wanted. The three example queries are precomputed and shipped as static JSON, rendered on load with no network call. Serving that from the same scale-to-zero container was always a compromise. Split apart:

- The recruiter path is **genuinely instant, always** — no cold start, no waking state, no keepalive
- `05_frontend.md` §6's error fallback becomes **structurally true rather than hopeful**: the API can be down entirely and the page still shows real results
- Only custom queries and the Action touch compute

### Why one service

The original blueprint split Node/Express (webhooks, orchestration, GitHub API) from Python/FastAPI (ML). Collapsed to one Python service.

**Rationale.** The entire interesting surface of this project — chunking, embedding, hybrid retrieval, normalization — lives in the Python half. The Node half was webhook receiving and comment posting, which is CRUD. A two-service split would spend real complexity budget (network hop, serialization, cross-service error handling, multi-container orchestration) on the *boring* half of the system.

"I already knew Node" is a fact about the author, not a property of the system. **Knowing when not to add a service is the stronger signal.**

---

## 2. Indexing runs locally, not on the deployed service

**This is the most consequential architectural decision in the document.**

Indexing a 6,000-PR repository takes hours: thousands of rate-limited API calls plus embedding tens of thousands of hunks. It runs as a **local CLI script** (`scripts/index_repo.py`) that writes directly to Neon. It is not an endpoint and the deployed service never performs it.

**Rationale:**

1. **Free-tier hosting cannot run multi-hour jobs.** Cloud Run caps request timeouts and scales to zero; a long-running index would be killed mid-run.
2. **No job queue needed.** The blueprint's scaling answer involved adding Bull/Celery. Running indexing locally removes the requirement entirely rather than solving it.
3. **The deployed service becomes read-mostly.** It queries vectors and returns JSON. No background workers, no job state, no partial-failure recovery in production.
4. **The deployed service needs no GitHub write token.** See §6.

**Consequence:** the corpus is a snapshot. Re-indexing is a manual local operation. Incremental sync is deferred past day 50 — and this is honest for the actual use case, since a demo repository's history does not change meaningfully day to day.

---

## 3. Folder structure

```
pr-review-assistant/
├── app/                         # deployed service
│   ├── main.py                  # FastAPI app, lifespan, routes
│   ├── config.py                # env-backed settings
│   ├── db.py                    # asyncpg pool
│   ├── schemas.py               # pydantic request/response models
│   ├── auth.py                  # API-key dependency
│   └── retrieval/
│       ├── chunking.py          # diff → hunks
│       ├── embedding.py         # model load, encode, truncation tracking
│       ├── signals.py           # vector / file-overlap / BM25
│       ├── normalize.py         # per-query min-max
│       ├── scoring.py           # candidate set, weighted sum, ranking
│       └── reasons.py           # template rules
│
├── scripts/
│   ├── index_repo.py            # local indexing CLI
│   └── rebuild_bm25.py
│
├── ingest/                      # used only by scripts/
│   ├── github_client.py         # pagination, rate limits, backoff
│   ├── diff_parser.py
│   └── corpus_filter.py         # bots, lang-*, docs, release, housekeeping
│
├── eval/                        # OFFLINE — never imported by app/
│   ├── pool.py                  # candidate pooling across variants
│   ├── label.py                 # blind labeling CLI
│   ├── score.py                 # Recall@3, MRR, bootstrap CI
│   ├── agreement.py             # quadratic weighted kappa
│   └── artifacts/               # judgments.jsonl, queries.json, snapshot
│
├── frontend/                    # demo page
├── migrations/                  # 001_init.sql, 002_...
├── action/                      # action.yml + entry script
├── tests/
│
├── .cache/                      # GITIGNORED — raw GitHub API responses
│   ├── prs/                     # PR list pages, one JSON per page
│   └── diffs/                   # one file per PR number
│
├── HANDOFF.md                   # overwritten each session close
├── DECISIONS.md                 # append-only decision ledger
├── JOURNAL.md                   # append-only build narrative
├── Dockerfile
└── README.md
```

**`eval/` is deliberately outside `app/`.** The evaluation harness is offline and deployment-independent by design (`01_evaluation_protocol.md` §15). Importing it into the service would create a path where deployed state could influence a published number. `app/` must never import from `eval/`.

**`ingest/` is imported only by `scripts/`.** It is not shipped in the runtime path. The service never calls the GitHub API for indexing.

---

## 4. Endpoints

Three. That is the whole surface.

### `GET /health`

Unauthenticated. Returns readiness and whether the embedding model is loaded.

```json
{ "status": "ok", "model_loaded": true, "corpus_prs": 1043 }
```

**Purpose:** the GitHub Action pings this first to wake a scaled-to-zero Cloud Run instance (§7). It must be cheap and must not touch the database on the hot path beyond a cached count.

### `POST /analyze`

Authenticated via `X-API-Key`. Called by the GitHub Action.

```json
// request
{ "repo": "fastapi/fastapi", "pr_number": 16024, "diff": "<raw diff>" }

// response
{
  "query_pr": 16024,
  "results": [
    {
      "pr_number": 15992,
      "title": "fix: pass include/exclude/by_alias params to jsonable_encoder",
      "url": "https://github.com/fastapi/fastapi/pull/15992",
      "outcome": "closed_unmerged",
      "final_score": 0.71,
      "vector_score": 0.68,
      "file_score": 1.0,
      "bm25_score": 0.42,
      "reason": "Both modify fastapi/encoders.py with a similar change pattern"
    }
  ]
}
```

**The Action sends the diff in the request body.** The service does not fetch it from GitHub — that would require a GitHub token on the service. The Action already has the diff via its own scoped credentials.

Results are cached to `similarity_results` with the active weights (`02_data_models.md` §8).

### `GET /similar/{owner}/{repo}/{pr_number}`

Unauthenticated, read-only. Serves the demo frontend from cached results, computing on demand if absent. Rate-limited per IP.

**Why public:** the demo page must work for a recruiter who has no key. Exposure is limited — it reads a public repository's public PRs and returns rankings over them.

### Removed from the blueprint

| Endpoint | Reason |
|---|---|
| `POST /webhook/github` | Redundant with the GitHub Action; both detect PR-open. The Action is the cleaner deployment story and requires no webhook secret verification or public callback URL. |
| `POST /repo/connect`, `GET /repo/:id/status` | Indexing moved local (§2) |
| `POST /index/pr` | Same |
| `POST /eval/run` | The harness is offline; exposing it would let deployed state affect published numbers |

---

## 5. Indexing pipeline

Run locally: `python scripts/index_repo.py --repo processing/p5.js`

```
1. Fetch PR list      → paginated, 100/page  (~60 requests for 6,000 PRs)
                      → WRITE RAW JSON TO .cache/prs/ BEFORE PARSING
2. Apply corpus filter → mark in_corpus / exclusion_reason
3. Fetch diffs        → ONLY for in_corpus PRs  (~1,000 requests)
                      → WRITE RAW DIFF TO .cache/diffs/<number>.diff
4. Parse into hunks   → file exclusions applied  ← reads from .cache/, not the API
4b. Zero-hunk filter  → no hunks left after step 4 ⇒ mark in_corpus = FALSE,
                        exclusion_reason = 'no_source_content'
5. Embed in batches   → record token_count, was_truncated
6. Write chunks       → ON CONFLICT DO NOTHING
7. Update repos.indexed_prs
```

**Step 2 before step 3 is the critical ordering.** Filtering on cheap list metadata *before* fetching per-PR diffs avoids roughly 5,000 wasted requests — the difference between one rate-limit window and three.

### The cache is not an optimization

**Fetching and parsing are separate stages, and everything downstream of step 3 reads from disk.**

The parser will have bugs. Chunking is the highest edge-case-density code in the project (`07_testing.md` §2), and some of those cases only appear in real diffs you have not seen yet. Without a cache, every parser fix costs a full re-fetch: roughly 1,000 rate-limited requests, potentially spanning more than one hourly window.

**With the cache, a chunking bug costs a re-parse — seconds.**

Rules:

- `--refresh` re-fetches; **the default always reads the cache when present**
- Cache writes happen *before* any parsing, so a parser crash never loses fetched data
- `.cache/` is gitignored (large, regenerable, and repository-specific)
- Cached responses are the frozen corpus snapshot the evaluation harness depends on (`01_evaluation_protocol.md` §15)

This follows the general rule in `11_workflow.md` §6: **any step over ten minutes gets its checkpoint built before the first run, not after the first failure.**

### Why a second filter pass exists

Step 2 filters on list metadata, which is all that is available before diffs are fetched — and that ordering is what saves ~5,000 requests. But some PRs are only identifiable as non-code **from their file list**: a translation-only PR is human-authored, carries no distinguishing label on `processing/p5.js`, and is invisible to every metadata rule.

Step 4b catches them on content. It costs **zero extra API requests** — it runs on a diff already fetched at step 3 and already parsed at step 4 — so the step-2-before-step-3 ordering is untouched.

**Why chunk-level exclusion alone is not enough.** Excluding locale JSON at step 4 removes only the vector signal. File overlap would still score a translation PR against every other translation PR at Jaccard ≈ 1.0, and BM25 would match on `translation.json` and near-identical titles. Two of three signals would fire at ceiling on content that means nothing. `in_corpus = FALSE` removes the PR from candidate-set construction entirely (`03_retrieval_engine.md` §4 step 1), which is the only place that closes all three.

Mark, never delete (`02_data_models.md` §4) — a wrongly-excluded PR is one `UPDATE` away from returning.

### Rate-limit handling

Authenticated GitHub REST allows **5,000 requests/hour**. At roughly two requests per indexed PR, a full corpus run sits close to that ceiling.

```python
# after every response
remaining = int(resp.headers["X-RateLimit-Remaining"])
if remaining < 100:
    reset_at = int(resp.headers["X-RateLimit-Reset"])
    sleep(reset_at - time.time() + 5)
```

Plus:
- **Exponential backoff** on 403 and 429
- **Fixed delay between requests** — GitHub's secondary rate limiter penalizes rapid bursts independently of the hourly quota
- **Resumability.** The run will be interrupted. `UNIQUE (repo_id, number)` and `UNIQUE (pr_id, file_path, hunk_index)` make re-runs idempotent; the script resumes from the highest indexed PR number.

**Never** hard-fail the whole run on a single PR error. Log it, mark it, continue.

---

## 6. GitHub Action

```yaml
name: PR Review Assistant
on:
  pull_request:
    types: [opened]

jobs:
  find-similar:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - name: Wake service
        run: |
          for i in {1..12}; do
            curl -sf "$SERVICE_URL/health" && break
            sleep 10
          done

      - name: Fetch diff and analyze
        id: analyze
        continue-on-error: true
        run: python action/entry.py

      - name: Post comment
        if: steps.analyze.outcome == 'success'
        uses: actions/github-script@v7
```

### The Action posts the comment, not the service

Two options existed. The Action posting is correct:

| | Service posts | **Action posts** |
|---|---|---|
| GitHub write token | Stored on the service | **Uses built-in `GITHUB_TOKEN`** |
| Permission scope | Broad, long-lived | **Scoped to the run, expires** |
| Works on third-party repos | Needs an App install | **Works wherever the Action is installed** |

**Consequence: the deployed service holds no GitHub credentials at all.** It receives a diff, returns JSON. That is the entire contract.

### Failure is non-fatal

`continue-on-error: true` on the analyze step, and the comment step is conditional. **A failure in this tool must never fail someone's pull request.** A missing comment is a non-event; a red check on an unrelated PR is a real cost.

---

## 7. Cold start handling

Cloud Run **scales to zero**: with no traffic, no instance exists. The next request starts a container, pulls the image, imports torch, and loads MiniLM in the lifespan handler.

**This is the project's one genuinely unmeasured risk.** It could be 15 seconds or 60. The number does not exist until Phase 3 puts a model in the lifespan handler — and it is the number that decides whether this hosting choice works.

**Mitigations, in order of preference:**

1. **CPU-only torch wheel** — the default PyPI wheel bundles CUDA libraries this service never uses. Measured: **1.6 GB → 433 MB**. Same weights, same embeddings, same published numbers, much shorter image pull. See §9.
2. **Model weights baked into the image at build time** — never downloaded at boot.
3. **Warmup call in the Action** — poll `/health` before `/analyze`, so the cold start happens while the Action waits rather than inside the analyze request.
4. **`--min-instances=1`** — eliminates cold starts entirely, and eliminates "free" with them, since idle instances bill for memory. **Last resort.**

**No keepalive.** Under the v1.1 design a scheduled ping kept a sleeping Hugging Face Space warm for the demo page. That is now unnecessary: the demo is static and never touches compute (§1). Pinging Cloud Run on a schedule would burn free-tier vCPU-seconds to solve a problem the architecture no longer has.

**Measure at Phase 3, not now** (`09_timeline_and_milestones.md` §3). Deciding hosting on an estimate is how this section came to be rewritten in the first place.

---

## 8. Auth and secrets

| Secret | Held by | Purpose |
|---|---|---|
| `API_KEY` | GitHub Action secret **and** Cloud Run secret | Gates `POST /analyze` |
| `DATABASE_URL` | Cloud Run secret; local `.env` | Neon connection (pooled, `sslmode=require`) |
| `GITHUB_TOKEN` (PAT) | Local `.env` only | Indexing. **Never deployed.** |
| `GITHUB_TOKEN` (built-in) | Action runtime | Comment posting. Ephemeral. |

**Secrets go in Secret Manager and are mounted as environment variables**, or are set with `--set-secrets` at deploy. **Never `--set-env-vars`.** Environment variables set that way are visible in the service's configuration page and in `gcloud run services describe` output.

> **This has already gone wrong once.** During day-1 setup, `DATABASE_URL` and `API_KEY` were added to a hosting platform as *public variables* rather than secrets, and both had to be rotated. The pattern to watch for: a platform offering two similar-looking fields, only one of which is private. **Read the field label before pasting a credential.**

The service URL is public and reachable by anyone. `POST /analyze` is therefore key-gated — without it, the endpoint is free compute for strangers. `.env` is gitignored; `.env.example` documents every variable with placeholder values.

### CORS

New in v1.2, and a direct consequence of splitting the frontend (§1). The static demo page calls `GET /similar/...` from a different origin.

- Allow **only** the static host's origin — never `*`
- `GET` only; `POST /analyze` is called by the Action, not a browser
- The origin is configuration, not a constant, so local development and production can differ

---

## 9. Deployment

**Google Cloud Run** for the API. **Any static host** for the demo page.

### Why not Hugging Face Spaces

The original target. As of July 2026, Hugging Face requires a paid plan (PRO, $9/mo) to create Docker Spaces; Static Spaces remain free. No changelog entry — it surfaced only as a "Paid" badge in the New Space form.

Alternatives were compared against one constraint: **the resident footprint with torch imported and MiniLM loaded**, estimated at 700 MB–1.2 GB and **still unmeasured** (§7).

| Host | Free memory | Verdict |
|---|---|---|
| Render | 512 MB, 0.1 CPU | Disqualified — OOM on model load |
| Koyeb | 512 MB | Disqualified |
| Railway | ~512 MB after trial | Disqualified |
| **Cloud Run** | **Configurable** | **Viable** — the only one that lets you choose |

Memory, not price, is what eliminates the others.

### Free tier

Verified July 2026: **180,000 vCPU-seconds, 360,000 GiB-seconds, and 2 million requests per month**, plus 1 GB of North American egress.

**Always Free applies only in `us-central1`, `us-east1`, and `us-west1`.** Deploying elsewhere silently forfeits it. Put the Neon project in a US region too, so the database is near the service rather than across an ocean.

A billing account must be linked even inside Always Free. **Set a budget alert at $1** — not because $1 matters, but because it makes an unexpected charge arrive as a notification rather than as a surprise on a statement.

### Image size and Artifact Registry

**Artifact Registry gives 0.5 GB free, then $0.10/GB/month.** The image is **433 MB** after the CPU-only torch change — under the free tier, but not by much.

**Every deployed revision pushes a new image.** A handful of revisions crosses 0.5 GB and starts billing. Set an Artifact Registry **cleanup policy** to keep only the most recent few, or delete old images manually. Without one, the storage bill grows quietly with each deploy.

### Dockerfile

Two things the container must get right:

```dockerfile
# CPU-only torch first. The default PyPI wheel bundles CUDA libraries this
# service never uses — same weights, same embeddings, roughly a quarter the
# image. Installed separately because +cpu wheels are Linux/Windows only, so
# the pin cannot live in requirements.txt without breaking macOS local installs.
RUN pip install --no-cache-dir torch==2.3.1 \
    --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bind $PORT when the platform injects one (Cloud Run does), else 7860 locally.
ENV PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

`requirements.txt` still pins `torch==2.3.1`, and pip treats `2.3.1+cpu` as satisfying it — so the second install step sees torch present and skips it. **The pin holds** (`06_code_standards.md` §11).

- **Port is `$PORT` with a 7860 default**, not a hardcoded 7860. Cloud Run injects `$PORT`; a service that ignores it never receives traffic. The default keeps local testing unchanged.
- **`--host 0.0.0.0`** matters equally: bound to localhost, the container answers only itself.
- **Build for `linux/amd64`.** On Apple Silicon this runs under emulation — expect 10–20 minutes, not seconds:

  ```bash
  docker build --platform linux/amd64 -t pr-review-assistant .
  ```

- Model weights baked in at build time, never downloaded at boot.
- Neon's **pooled** connection string, since instances start and stop constantly.

**Local development** uses `docker-compose.yml` with Postgres + pgvector, so the eval harness runs against a local snapshot with no network dependency.

---

## 10. Logging and errors

- Structured JSON to stdout — Cloud Run ingests stdout into Cloud Logging automatically, and structured JSON is parsed into queryable fields.
- Log at ingest: PRs fetched, filtered (by reason), chunks created, truncation count.
- Log at query: query PR, candidate count, per-signal ranges before normalization, final top 3.

**Per-signal ranges are worth logging deliberately.** A BM25 range of `[0, 14.2]` next to a cosine range of `[0.1, 0.7]` is the raw evidence for why normalization exists — useful in debugging and directly quotable in an interview.

Errors return structured JSON with a request ID. Retrieval failure returns 503, not 500 — the Action should treat it as retryable.

---

## 11. Checklist

- [ ] `app/` never imports from `eval/`
- [ ] Indexing exists only as a local script, not an endpoint
- [ ] Corpus filter applied before diff fetching
- [ ] **Raw responses cached to `.cache/` before parsing; parser reads from disk**
- [ ] **`--refresh` flag exists; default reads the cache**
- [ ] Rate-limit headers checked; backoff and inter-request delay implemented
- [ ] Indexing resumable and idempotent
- [ ] Service holds no GitHub credentials
- [ ] Action posts the comment using the built-in token
- [ ] Analyze step is `continue-on-error`
- [ ] Warmup loop before `/analyze`
- [ ] Model loaded in lifespan, not per request
- [ ] Container binds `$PORT` with a 7860 default, host `0.0.0.0`
- [ ] Image built `--platform linux/amd64`
- [ ] CPU-only torch installed in the Dockerfile, not pinned in `requirements.txt`
- [ ] Deployed to `us-central1`, `us-east1`, or `us-west1`; Neon in a US region
- [ ] Secrets via Secret Manager, never `--set-env-vars`
- [ ] CORS allows only the static host's origin
- [ ] Budget alert set at $1
- [ ] Artifact Registry cleanup policy configured
- [ ] `.env.example` complete; `.env` gitignored
