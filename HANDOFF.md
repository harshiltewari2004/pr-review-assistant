# Handoff — 2026-07-29, end of Phase 1 Day 6 (Phase 2 pulled forward)

## Done and committed
- ingest/constants.py: four exclusion_reason literals named
  (bot_author, housekeeping, duplicate_resubmission, no_source_content),
  BOT_ACCOUNTS, HOUSEKEEPING_TITLE_PATTERNS, DUPLICATE_WINDOW_DAYS=7,
  TITLE_SIMILARITY_THRESHOLD=0.95. no_source_content is defined here but
  APPLIED at 04 §5 step 4b in the parser, not in corpus_filter.
- ingest/corpus_filter.py: PRMeta, Verdict, classify(), normalize_title(),
  titles_match(), group_duplicates(), pick_keeper(), apply_corpus_filter(),
  report_housekeeping_near_misses().
- Duplicate pass runs on SURVIVORS of classify() only — bots must not land
  in the duplicate bucket or the 02 §4 audit reports the wrong reason.
- tests/test_corpus_filter.py: 8-PR golden fixture. Counter printed and read:
  {None: 3, bot_author: 2, duplicate_resubmission: 2, housekeeping: 1}.
- Invariant asserted: exclusion_reason IS NULL exactly when in_corpus.

## Deployed state
- Unchanged. Not deployed (Cloud Run is Phase 7 per 04 §9). Skeleton builds
  locally, 433 MB.
- Neon: schema v001, 6 tables, empty. Migration 002 (judgments.self_authored)
  still unwritten — free any time, needed before Phase 5.
- pgvector 0.8.0 Neon / 0.8.5 local docker (D-P1-3).

## Sequencing note — read before writing github_client.py
corpus_filter.py was built at Day 6, ahead of github_client.py (09 §3 puts
the client at days 8-9 and the filter at day 10). The contract therefore
flows filter -> client: github_client.py MUST produce ingest.corpus_filter
.PRMeta (number, title, author, author_type, created_at, merged_at) from the
/pulls list payload. from_list_item() belongs in github_client.py, NOT in
corpus_filter.py — the filter must not know GitHub's JSON key names.
Filter has NOT yet been run against real cached list pages.

## Open decisions carried forward
- D-P2-2 OPEN: 406 on large diffs — /pulls/{n}/files fallback vs log-and-skip.
  Decide when writing github_client.py. NOW THE NEXT THING DUE.
- D-P2-4 OPEN: "near-identical title" operationalized (normalized-exact OR
  ratio >= 0.95; 7-day window anchored to group's first member). Resolve by
  reading the logged duplicate groups after the first full list fetch.
- D-P2-5 OPEN: housekeeping patterns case-sensitive as written in 01 §2;
  case-only near-misses logged, not matched. Resolve from the same log.
- D-P3-1 OPEN: manual ::vector cast vs pgvector asyncpg codec. Phase 3.
- D-P3-2 OPEN: Neon pooled + asyncpg create_pool() under Cloud Run churn.
  Phase 7. statement_cache_size=0 is the known fallback.
- D-P5-2 OPEN: 01 §7 anchors and §8 subsystems carry STALE markers.
  Rewrite before Day 25.

## Carried-over obligations
- 01 §7 anchor rewrite: diffs for #8862, #8964, #8823 (~15 min with the
  Day-2 spike script) + p5.js /labels confirmed against the actual page.
  Not gated on D-P5-1.
- #8862 truncates hard: 2 of 3 source hunks over 256 tokens, range 64-614,
  median 387. Any anchor written against it says so.
- spikes/day5_doc_label_sample.py + day5_output.txt committed at 821ff17
  (before this session; I misremembered it as unrun). 10/10 sampled PRs
  carry substantive source changes against the >=3 pre-registration =>
  Documentation is a [facet | type] on p5.js. 01 §2 keeps no Documentation
  row either way; corpus_filter.py unchanged. The number is the one that
  explains the no_source_content count in the README at Phase 9.
- Migration 002 for judgments.self_authored.
- Reserved (CodeDay), Good First Issue, Help Wanted: process labels,
  NOT exclusions. Workflow state does not correlate with diff similarity.
- MAX vs mean-of-top-3: evidence exists as of Day 4 (p5.js Similar B
  full-diff winner was shared test scaffolding, 0.6788 -> 0.7074).
  Re-examine at Milestone A, not before.

## Decisions log watermark
- Current through D-P5-5... no: current through D-P2-5, committed.
  (D-P5-2 remains the highest-numbered Phase 5 entry.)

## Next session starts with
- Day 7: ingest/github_client.py (09 §3 days 8-9, also pulled forward).
  Paste the pagination + rate-limit + backoff loop from
  spikes/day2_github_api.py — that is plumbing, 11 §3.
  Type by hand: from_list_item() -> PRMeta, and the resumability logic.
  MUST cache raw responses to .cache/prs/ BEFORE parsing (04 §5, hot
  invariant 19). Cache write precedes parse so a parser crash loses nothing.
  Resolve D-P2-2 in this session — it is due when this file is written.
  Golden assertion: fetch one page, assert 100 items, assert every item
  maps to a PRMeta without KeyError, print the first record and read it.