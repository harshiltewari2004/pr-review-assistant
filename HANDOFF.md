# Handoff — 2026-07-28, end of Phase 1 Day 5 (doc revision pass)

## Done and committed
- Doc revision batch CLOSED. Eight docs retargeted to processing/p5.js.
  01 §2 rewritten: four metadata exclusion rules (bots + explicit account
  list, housekeeping title prefixes, duplicate resubmissions, no lang-*,
  no release), plus the content-based zero-hunk rule pointing at 04 §5 4b.
  No Documentation label row — p5.js uses it as a facet, not a type.
- 04 §5 gained step 4b: zero hunks after file exclusions ⇒ in_corpus =
  FALSE, exclusion_reason = 'no_source_content'. Costs no extra requests.
- 03 §2 excludes translations/*/translation.json, NOT translations/ —
  dev.js and index.js are the i18next loader and are real source.
- 03 §3 and 02 §5's normalize_embeddings reason corrected: <=> is already
  magnitude-invariant. Normalization buys agreement OUTSIDE Postgres.
- 02 §7: judgments.self_authored column added while the table is empty.
- 01 §12: re-test sample is stratified, not random — every self_authored
  pair enters, kappa computed twice, no kappa published under n=10.
- 08 §8a caveats converted from instruction to measured result.
- D-P1-2 reconciled, D-P5-1 CONFIRMED, D-P2-3 CONFIRMED.

## Deployed state
- Service: not deployed (Cloud Run is Phase 7 per 04 §9). Skeleton builds
  locally, 433 MB.
- Neon: schema v001, 6 tables, empty. Needs judgments.self_authored — the
  02 §7 column is in the doc, NOT in the database. Migration 002 required
  before Phase 5, free to write any time.
- pgvector 0.8.0 Neon / 0.8.5 local docker (D-P1-3).

## Open decisions carried forward
- D-P2-2 OPEN: 406 on large diffs — /pulls/{n}/files fallback vs
  log-and-skip. Decide when writing github_client.py. The Documentation
  sample spike exercises that endpoint incidentally.
- D-P3-1 OPEN: manual ::vector cast vs pgvector asyncpg codec. Measure at
  Phase 3 bulk insert.
- D-P3-2 OPEN: Neon pooled + asyncpg create_pool() under Cloud Run churn.
  Phase 7. statement_cache_size=0 is the known fallback.
- D-P5-2 OPEN: 01 §7 anchors and §8 subsystems. Both now carry STALE
  markers rather than being silently wrong. Rewrite before Day 25.

## Carried-over obligations
- 01 §7 anchor rewrite needs: diffs for #8862, #8964, #8823 (~15 min with
  the Day-2 spike script), and p5.js /labels confirmed against the actual
  page rather than list-view sampling. NOT gated on D-P5-1 — anchors are
  open rubric examples, not blind judgments.
- #8862 truncates hard: 2 of 3 source hunks over 256 tokens, range 64–614,
  median 387. Any anchor written against it says so.
- spikes/day5_doc_label_sample.py — confirmatory only, 11 requests.
  Pre-registered: ≥3/10 with source changes ⇒ Documentation is a facet and
  4b was the right mechanism; ≤2/10 ⇒ the two rules would have agreed.
- Migration 002 for judgments.self_authored.
- Reserved (CodeDay) is an event-claim marker, NOT an exclusion. Process
  labels describe workflow state; workflow state does not correlate with
  diff similarity. Same for Good First Issue and Help Wanted.
- MAX vs mean-of-top-3: real evidence exists as of day 4 (p5.js Similar B
  full-diff winner was shared test scaffolding, 0.6788 → 0.7074).
  Re-examine at Milestone A, not before.

## Decisions log watermark
- Current through D-P5-2, committed.

## Next session starts with
- Day 6: ingest/corpus_filter.py. Unblocked — every rule is either list
  metadata at 04 §5 step 2 or the zero-hunk check at 4b.
  Type the classify() logic by hand (06 §? logic-vs-plumbing); paste the
  pagination loop from spikes/day2_github_api.py.
  The three exclusion_reason literals go in ingest/constants.py, not
  inline — a typo splits the 02 §4 audit count silently.
  Golden assertion at build time (11 §8): a fixture PR set of one bot PR,
  one housekeeping PR, one duplicate triple, one docs-only PR, one mixed
  docs+code PR. Print the exclusion_reason breakdown and read it.