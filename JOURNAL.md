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