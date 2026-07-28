# PR Review Assistant — Day 1 Setup

**v1.2 — Locked July 2026**

*Changed from v1.1: §6 is now a local build verification, not a live deploy. Hugging Face began charging for Docker Spaces in July 2026; the deployment target is Google Cloud Run and belongs in Phase 7.*
*Changed from v1.0: §3 creates all three record-keeping files and gitignores `.cache/` (`06_code_standards.md` §12, `11_workflow.md` §1).*

Everything that must exist before any real code is written. Sequenced, with a verification gate after each step.

Consolidates the folder structure from `04_architecture.md` §3, tooling from `06_code_standards.md` §4, deployment from `04` §9, and secrets from `04` §8 into one runnable order.

**Target: one session, roughly 3.5 hours.** If it runs long, the container build (§6) is the one to push to day 2 — everything before it is required to start Phase 2.

---

## Why build the skeleton container on day 1

The original plan put the container spike on day 7. Moving it to day 1 is strictly better.

Deployment is the step most likely to surprise you — wrong port, Docker build quirks, secrets not injected, a container that builds and then never responds. Finding that on day 1 with a twelve-line app costs an hour. Finding it on day 38 with a real service costs a phase, because you cannot tell whether the problem is your code or the platform.

**Build a skeleton that does nothing, and prove the container works.** Fill it in later.

### What day 1 does and does not include

**It was going to be a live deploy to Hugging Face Spaces. It is not.** HF began requiring a paid plan for Docker Spaces in July 2026, and the replacement target — Google Cloud Run — is worth deferring for a better reason: **the number that decides whether Cloud Run works is the resident footprint with MiniLM loaded, and no model loads until Phase 3.**

So day 1 proves what it can prove locally: the image builds, torch installs, the container binds its port, `/health` answers. That was §6's real purpose all along; the hosting platform was incidental.

Cloud Run deployment is Phase 7 (`04_architecture.md` §9). This still frees day 7, which becomes buffer.

---

## 1. Accounts and credentials (~40 min)

| Account | Needed for | Notes |
|---|---|---|
| **GitHub** | Repo, Action, API access | Already have |
| **GitHub PAT** | Indexing script (`ingest/`) | Fine-grained token, **read-only, public repos**. Nothing more. |
| **Neon** | Postgres + pgvector | Free tier, no card |
| **Google Cloud** | Cloud Run — Phase 7, not today | Always Free; billing account required |

### GitHub token

Settings → Developer settings → Personal access tokens → **Fine-grained tokens**.

- Repository access: **Public repositories (read-only)**
- Expiration: 90 days — covers the build with margin
- No write scopes. The indexing script only reads.

**This token lives in local `.env` only and is never deployed** (`04_architecture.md` §8). The deployed service holds no GitHub credentials at all — comment posting uses the Action's built-in ephemeral token.

### Neon

1. Create a project. **Region: a US region**, so the database sits near the Cloud Run service that will read it (`04_architecture.md` §9). The eval harness runs locally, so your own latency to Neon barely matters; the service's does.
2. Copy **both** connection strings — pooled and direct.
   - **Pooled** → the deployed service, which restarts often
   - **Direct** → local scripts and migrations
3. Store both in local `.env`.

### Google Cloud — create the account, deploy nothing

Sign up and link a billing account. **Always Free still requires one**, which is the part people find alarming; the mitigation is a budget alert.

1. Create a project
2. **Set a budget alert at $1** — do this before anything else. It is not about the dollar; it is about an unexpected charge arriving as a notification rather than as a statement.
3. Stop there. No Cloud Run service, no Artifact Registry repository. Those are Phase 7.

**Region, when you get there: `us-central1`, `us-east1`, or `us-west1` only.** Always Free applies nowhere else, and deploying to a nearer region silently forfeits it.

**Verification gate:** all four credentials sitting in a local `.env` file that is already gitignored.

---

## 2. Local environment (~20 min)

```bash
python3.11 --version     # 3.11+ required (06_code_standards.md §1)
docker --version         # for local Postgres + pgvector
git --version
```

Install Python 3.11+ if missing. Docker Desktop if missing — needed for the local test database (`07_testing.md` §6), not optional.

```bash
mkdir pr-review-assistant && cd pr-review-assistant
git init
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

**Verification gate:** `which python` points inside `.venv`.

---

## 3. Repo scaffold (~30 min)

Create the full structure from `04_architecture.md` §3 up front. Empty directories are cheap; deciding where a file goes at 11pm on day 23 is not.

```bash
mkdir -p app/retrieval scripts ingest eval/artifacts frontend migrations action tests/{unit,integration,fixtures/diffs}
touch app/{__init__,main,config,db,schemas,auth}.py
touch app/retrieval/{__init__,chunking,embedding,signals,normalize,scoring,reasons,constants}.py
touch ingest/{__init__,github_client,diff_parser,corpus_filter}.py
touch eval/{__init__,pool,label,score,agreement}.py
touch tests/conftest.py
```

### Files that must exist on day 1

**`.gitignore`**

```
.venv/
__pycache__/
*.pyc
.env
.pytest_cache/
.ruff_cache/
.cache/
eval/artifacts/corpus_snapshot.json
```

`.cache/` holds raw GitHub API responses (`04_architecture.md` §5) — large, regenerable, and repository-specific.

**`.env`** (gitignored) and **`.env.example`** (committed, placeholders only):

```bash
GITHUB_TOKEN=github_pat_xxx
DATABASE_URL=postgresql://...        # pooled — service
DATABASE_URL_DIRECT=postgresql://... # direct — scripts, migrations
API_KEY=generate_a_long_random_string
SERVICE_URL=https://<service>-<hash>-<region>.a.run.app  # Phase 7; empty until then
```

Generate `API_KEY` now: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

**Loading `.env` in a shell:** use `set -a && source .env && set +a`. Do **not** parse it with `grep | cut` — that keeps the wrapping quotes, so `$GITHUB_TOKEN` becomes `'github_pat_...'` and every API call returns `401 Bad credentials` with a valid token. The symptom is identical to an unset variable and to a revoked token. `echo ${#GITHUB_TOKEN}` separates them: a fine-grained PAT is **93** characters. The same trap applies to `DATABASE_URL`.

**`pyproject.toml`** — ruff config exactly as specified in `06_code_standards.md` §4.

**`requirements.txt`** — pinned versions from `06` §11. Pin on day 1, not later; a floating `sentence-transformers` that shifts mid-build silently changes your embeddings and invalidates published numbers.

**Three record-keeping files** — all created today, with different lifecycles (`06_code_standards.md` §12).

`JOURNAL.md` — append-only narrative. First entry today, two minutes:

```markdown
# Build Journal

## 2026-XX-XX — Day 1
Setup. [What broke, what surprised you, what took longer than expected.]
```

`DECISIONS.md` — the ledger. Header plus the first entry:

```markdown
# Decisions

### D-P1-1 — CONFIRMED (2026-XX-XX)
Skeleton deploys on day 1 rather than day 7. Deployment is the step most
likely to surprise; finding platform friction now costs an hour, finding
it on day 38 costs a phase. See 08_setup.md intro.
```

`HANDOFF.md` — overwritten at every session close, template in `11_workflow.md` §1. Write the first one at the end of today. **This is the file you paste as message one of every future session**, so getting it started on day 1 is what makes the habit stick.

**`README.md`** — one-line stub. The real one is days 48–50.

**`app/retrieval/constants.py`** — copy the constant block from `06` §6 verbatim, including the starting weights. Having them in one place from the first commit prevents magic numbers leaking into logic later.

```bash
pip install -r requirements.txt
ruff check .
git add -A && git commit -m "Initial project scaffold"
```

**Verification gate:** `ruff check .` passes, first commit exists.

---

## 4. Local database (~20 min)

**`docker-compose.yml`:**

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_PASSWORD: dev
      POSTGRES_DB: prreview
    ports: ["5432:5432"]
```

```bash
docker compose up -d
docker compose exec db psql -U postgres -d prreview -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

The `pgvector/pgvector` image ships the extension preinstalled — using plain `postgres` means compiling it yourself.

**Verification gate:**

```sql
SELECT '[1,2,3]'::vector;
```

Returns without error.

---

## 5. Migration 001 (~25 min)

Write `migrations/001_init.sql` from `02_data_models.md` — all six tables, their indexes, and the `vector` extension. It is already written as DDL there; this is transcription, not design.

Apply to **both** databases:

```bash
psql "$DATABASE_URL_DIRECT" -f migrations/001_init.sql   # Neon
psql "postgresql://postgres:dev@localhost/prreview" -f migrations/001_init.sql
```

Local and Neon must stay in sync from the start. Divergence discovered in week 6 is painful to reconcile.

**Verification gate:** `\dt` lists six tables on both. On Neon specifically:

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

---

## 6. Skeleton container build (~60 min)

The step most likely to surprise you. Do it now, with nothing in it.

**`app/main.py`:**

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": False, "corpus_prs": 0}
```

**`Dockerfile`:**

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# CPU-only torch first. The default PyPI wheel bundles CUDA libraries this
# service never uses. Installed separately because +cpu wheels are Linux and
# Windows only, so the pin cannot live in requirements.txt without breaking
# macOS local installs. See 06_code_standards.md §11.
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

**`$PORT` with a 7860 default, not a hardcoded port.** Cloud Run injects `$PORT` and routes nothing to a service that ignores it. The default keeps local testing unchanged and makes the container portable across hosts — which, given that this project has already changed hosts once, is worth having.

**`--host 0.0.0.0`** matters equally: bound to localhost, the container answers only itself.

### Build and run it locally

```bash
docker build -t pr-review-assistant .
docker images pr-review-assistant --format "{{.Size}}"
docker run --rm -d -p 7860:7860 --name prra pr-review-assistant
sleep 5
curl -s localhost:7860/health
docker stop prra
```

Expect roughly **430 MB**. Without the CPU-only torch step it is around 1.6 GB — if you see that, the CPU index did not take, and the build log will say why.

**Verification gate:**

```json
{"status":"ok","model_loaded":false,"corpus_prs":0}
```

If this returns, the image builds, torch installs, and the container binds correctly. Everything §6 was ever meant to prove is proven.

### One extra check if you are on Apple Silicon

Cloud Run runs `amd64`. Building the target explicitly now surfaces any architecture problem while the app is twelve lines:

```bash
docker build --platform linux/amd64 -t pr-review-assistant-amd64 .
```

**This is slow** — pip runs under emulation, so expect 10–20 minutes rather than seconds. Worth knowing now rather than in the middle of Phase 7.

### Do not put credentials anywhere yet

There is no deployed service, so there is nothing to configure. `DATABASE_URL` and `API_KEY` stay in local `.env` until Phase 7 puts them in Secret Manager (`04_architecture.md` §8).

**When that day comes: read the field label before pasting.** A credential entered into a platform's *variables* field instead of its *secrets* field is a public credential — this has already happened once on this project, and cost two rotations.

---

## 7. Deferred to later phases

Deliberately **not** day-1 work:

| Item | When | Why |
|---|---|---|
| `pre-commit` hooks | Week 3 (`06` §4) | Friction while the codebase is still changing shape |
| GitHub Action | Phase 7 | Nothing to call yet |
| Cloud Run deployment | Phase 7 | The footprint measurement that validates it does not exist until Phase 3 |
| Frontend files | Phase 8 | — |
| Test fixtures | Phase 1 spike | Collected while fetching real diffs |
| Model download in Docker | Phase 3 | Adds minutes to every build; not needed to prove the pipe |

---

## 8. Revised Phase 1

With deployment done on day 1, the spikes compress:

| Day | Work |
|---|---|
| **1** | This document |
| **2** | GitHub API spike — pagination, rate-limit headers, backoff. **Save 7 fixture diffs** (`07_testing.md` §4) including the `@@`-in-content case. |
| **3** | Neon + pgvector spike — insert one 384-dim vector from Python, query it back by cosine |
| **4** | **Embedding sanity spike, both repos** — embed known-similar PR pairs from FastAPI (Python) *and* `processing/p5.js` (JavaScript), plus **a size-matched negative control per repo**. Python validates the plan as written; JavaScript tests whether the vector signal generalizes — MiniLM is a natural-language model and has only ever been validated on Python here. **Verify every pair from its diff, not its title**, or file-overlap and BM25 carry the result and the vector signal is never actually tested. **The number recorded is the gap**, not the raw cosine (§8a). Resolves `D-P1-2` and `D-P1-4`. |
If both languages return reasonable cosines, that is direct evidence for the "repository-agnostic architecture" claim — not an assumption. If JavaScript is meaningfully weaker, that gap is now measured, which is its own interview point.
| **5–7** | Buffer, or start Phase 2 early |

### 8a. Day 4 — verified pairs and the gap criterion

**Raw cosine is uninterpretable.** Unrelated code diffs share large vocabulary — `+`, `-`, `if`, `return`, import lines, brace syntax — so two unrelated JavaScript diffs can score 0.55 on boilerplate alone. Only the **gap between a similar pair and a size-matched control** carries information.

Every similar pair therefore gets a negative control: a known-unrelated PR from the same repository and era, of comparable diff size. Size matching matters — pairing a 3-line diff against a 300-line one depresses cosine through shape mismatch alone, and that gap would be unearned.

**Pairs, verified from diffs (not titles):**

| Repo | Role | PRs | Property |
|---|---|---|---|
| FastAPI | Similar A | #15994 ↔ #15992 | Different files (`encoders.py` / `routing.py`) — Jaccard 0.0, pure vector test |
| FastAPI | Similar B | #15937 ↔ #15813 | Same file, same code block, would merge-conflict |
| FastAPI | Control | #15992 ↔ #15515 | `routing.py` / `sse.py` — size ratio ~4×, imperfect |
| p5.js | Similar A | #8829 ↔ #8933 | Two solutions to the same static-method problem, one superseded (§6 rule 4). Different files |
| p5.js | Similar B | #8823 ↔ #8862 | Both add FES errors to strands; 2 of 6 files shared |
| p5.js | Control | #8829 ↔ #8964 | Vector/FES vs framebuffer density — size ratio ~1.3× |

**Known bias:** the FastAPI control is worse size-matched than the p5.js control, which inflates FastAPI's gap. This biases *against* p5.js, so a comparable p5.js result is a stronger finding, not a weaker one. State it with the numbers rather than correcting it.

**Caveats, now measured** (run 2026-07-27, `spikes/day4_output.txt`):

- **Similar A is single-hunk on the FastAPI side only.** `#15994` and `#15992` are one hunk each, so that pair says nothing about chunk→PR aggregation. `#8829` carries three hunks against `#8933`'s one, so p5.js's Similar A does exercise `MAX` across query hunks. A small asymmetry, worth remembering when the two figures are compared.
- **`#15813`'s `.md` file was excluded at chunk level as required.** No `.md` content reached the model in any configuration.
- **`#15937`'s new test file measured 3,698 tokens in one hunk** — 14× the 256-token limit, truncated as predicted. Similar B was measured both ways, and the two repositories diverged:

| | source-only MAX | full MAX | winning hunk changed? |
|---|---|---|---|
| FastAPI | 0.8376 | 0.8376 | No — the source hunk wins both |
| p5.js | 0.6788 | 0.7074 | **Yes** — a test hunk wins the full run |

  For FastAPI the giant truncated test hunk did not distort the result. For p5.js it did: the full-diff winner is `test/unit/webgl/p5.Shader.js` on *both* sides, opening with the identical string `test('returns numbers for builtin globals outside hooks and…`. **The top match is shared test scaffolding, not shared change semantics.** That is `03_retrieval_engine.md` §5's named `MAX` weakness — *"one coincidental hunk match inflates an entire PR's score"* — appearing on real data at day 4, and it is the first concrete argument for the mean-of-top-3 comparison §5 defers to tuning. Re-examine at Milestone A (`09_timeline_and_milestones.md` §4).

- **`#8862` truncates hard.** Two of its three source hunks exceed 256 tokens (range 64–614, median 387). Any anchor written against it is written against a partly-truncated vector representation, and the anchor's note should say so.
- **Truncation across the spike: 9 of 32 hunks (28%)**, near-identical between repositories (FastAPI 3/11, p5.js 6/21). **This figure goes in no document.** The sample is n=32 across ten deliberately size-matched PRs, one of which was selected *because* it truncates. It is recorded in `JOURNAL.md` as the Phase 3 prediction; the corpus-wide rate arrives at the Day 19 index run (`02_data_models.md` §5).
**Day 4 is the one that matters.** It is the only assumption in the entire plan that could reshape the project. If two genuinely similar PRs come back at cosine 0.2, the vector signal is weaker than assumed and `03_retrieval_engine.md` needs rebalancing toward file overlap and BM25 — a decision far better made on day 4 than day 34.

---

## 9. Checklist

- [ ] GitHub fine-grained PAT, read-only public repos
- [ ] Neon project created in a **US region**; pooled **and** direct connection strings saved
- [ ] Google Cloud account created, billing linked, **budget alert set at $1**
- [ ] Python 3.11+ venv active
- [ ] Docker running
- [ ] Full folder structure from `04` §3 created
- [ ] `.gitignore` includes `.env`
- [ ] `.env.example` committed with every variable
- [ ] `API_KEY` generated
- [ ] `requirements.txt` fully pinned
- [ ] `constants.py` populated from `06` §6
- [ ] `JOURNAL.md`, `DECISIONS.md`, and `HANDOFF.md` all created with a day-1 entry
- [ ] `.cache/` gitignored
- [ ] `ruff check .` passes
- [ ] Local Postgres running with `vector` extension
- [ ] `001_init.sql` applied to **both** local and Neon
- [ ] Six tables verified on both
- [ ] Dockerfile installs CPU-only torch and binds **`$PORT`** with a 7860 default
- [ ] Image built and run locally; size ≈ 430 MB
- [ ] `curl localhost:7860/health` returns `{"status":"ok"}`
- [ ] `--platform linux/amd64` build verified (Apple Silicon only)
- [ ] No credentials placed on any hosting platform
- [ ] First commit pushed to GitHub
