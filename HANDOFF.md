# Handoff — 2026-07-30, end of Phase 1 Day 7 (Phase 2 pulled forward)

## Done and committed
- Golden assertion GREEN on first successful run: page 1 = #16 (2013-07-02)
  -> #335 (2014-08-22), ascending, tz-aware UTC. D-P2-6 confirmed on real data.
- tests/test_github_client.py NOT written — deferred until PRMeta gains
  author_type (D-P2-7), since the fixture shape changes.- PRMeta's real field names live in corpus_filter.py, not in a handoff summary.
  Audit against the dataclass signature, not against prose.
- ingest/constants.py: GitHub client block added — GITHUB_API_ROOT,
  DIFF_MEDIA_TYPE, PER_PAGE=100, LIST_STATE='all', LIST_SORT='created',
  LIST_DIRECTION='asc', INTER_REQUEST_DELAY_S=0.75, RATE_LIMIT_FLOOR=100,
  MAX_BACKOFF_ATTEMPTS=5, cache paths, GHOST_AUTHOR, and the FIFTH
  exclusion_reason literal EXCLUSION_DIFF_UNAVAILABLE='diff_unavailable'.
- ingest/github_client.py: GitHubClient, DiffUnavailable, _request()
  (backoff on 403/429, honours Retry-After), _respect_rate_limit(),
  from_list_item() -> PRMeta, _parse_ts(), _cache_path(),
  _read_cached_page(), _fetch_list_page(), iter_list_pages(),
  iter_pr_meta(), fetch_diff().
- Contract direction enforced by the import: github_client imports
  corpus_filter.PRMeta, never the reverse.
- Cache write precedes every parse; both fetchers read back from disk
  rather than from the response object.
- tests/test_github_client.py: from_list_item over two saved fixture items
  including the "user": null ghost case. Runs offline.
- Live smoke run: page 1 of processing/p5.js, 100 items, all mapped,
  first/last PRMeta printed and READ — dates confirmed <FILL IN>, which is
  what proves direction=asc took effect.

## Deployed state
- Unchanged. Not deployed (Cloud Run is Phase 7 per 04 §9). Skeleton builds
  locally, 433 MB.
- Neon: schema v001, 6 tables, empty. Migration 002 (judgments.self_authored)
  still unwritten — free any time, needed before Phase 5.
- pgvector 0.8.0 Neon / 0.8.5 local docker (D-P1-3).
- .cache/prs/ now holds real p5.js list pages. .cache/ is gitignored.

## Read before writing diff_parser.py
- additions and deletions are NOT in the /pulls list payload — they exist
  only on GET /pulls/{n}, which would cost ~1,000 extra requests for two
  integers. Derive both from the parsed diff at 04 §5 step 4. Same for
  files_changed. Do not reach for a re-fetch at day 13.
- diff_unavailable is applied at step 3 by catching DiffUnavailable. It is
  NOT the parser's job and NOT the same thing as no_source_content:
  406 means too much content, 4b means none.
- CACHE COLLISION, UNVERIFIED: .cache/diffs/<number>.diff has no repo
  namespace (04 §3 as written), but 02 §9 keeps the Day-4 FastAPI diffs in
  .cache/. FastAPI and p5.js number spaces overlap — #8862 exists in both.
  CHECK what spikes/day4_*.py wrote before the first ingest run. If it
  collides, namespace to .cache/diffs/<owner>__<repo>/ and log D-P2-7.

## Open decisions carried forward
- D-P2-4 OPEN: "near-identical title" operationalized (normalized-exact OR
  ratio >= 0.95; 7-day window anchored to group's first member). Resolve by
  reading the logged duplicate groups after the first full list fetch —
  the client that produces that fetch now exists.
- D-P2-5 OPEN: housekeeping patterns case-sensitive as written in 01 §2;
  case-only near-misses logged, not matched. Resolve from the same log.
- D-P3-1 OPEN: manual ::vector cast vs pgvector asyncpg codec. Phase 3.
- D-P3-2 OPEN: Neon pooled + asyncpg create_pool() under Cloud Run churn.
  Phase 7. statement_cache_size=0 is the known fallback.
- D-P5-2 OPEN: 01 §7 anchors and §8 subsystems carry STALE markers.
  Rewrite before Day 25.

## Carried-over obligations
- 01 §7 anchor rewrite: diffs for #8862, #8964, #8823 — now a fetch_diff()
  call rather than a spike-script run. Plus p5.js /labels confirmed against
  the actual page. Not gated on D-P5-1.
- #8862 truncates hard: 2 of 3 source hunks over 256 tokens, range 64-614,
  median 387. Any anchor written against it says so.
- Documentation is a [facet | type] on p5.js — 10/10 sampled PRs carry
  substantive source changes (spikes/day5_doc_label_sample.py, 821ff17).
  01 §2 keeps no Documentation row; corpus_filter.py unchanged. The number
  explains the no_source_content count in the README at Phase 9.
- README at Phase 9 now owes FIVE exclusion counts, not four.
- Migration 002 for judgments.self_authored.
- Reserved (CodeDay), Good First Issue, Help Wanted: process labels,
  NOT exclusions.
- MAX vs mean-of-top-3: evidence exists as of Day 4 (p5.js Similar B
  full-diff winner was shared test scaffolding, 0.6788 -> 0.7074).
  Re-examine at Milestone A, not before. D-P2-2 leans on the same evidence.
- 04 §5 needs a step 3b line for diff_unavailable when the doc revisions
  are made.

## Decisions log watermark
- Current through D-P2-6, committed. D-P2-2 and D-P2-6 both RESOLVED today.
  D-P5-2 remains the highest-numbered Phase 5 entry.

## Next session starts with
- Day 8: run the full list fetch on processing/p5.js (~44 pages under
  state=all, ~1% of quota) and pipe it through apply_corpus_filter().
  This is the first time the filter meets real data — it closes D-P2-4 and
  D-P2-5 from the logged duplicate groups and housekeeping near-misses.
  Print the exclusion_reason Counter and READ it (11 §5). Expect four
  reasons, not five — diff_unavailable cannot appear until step 3.
  Verify the .cache/diffs/ collision question BEFORE any diff fetching.