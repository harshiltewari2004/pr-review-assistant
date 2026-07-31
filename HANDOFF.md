# Handoff — 2026-07-31, end of Phase 1 Day 7 (Phase 2 pulled forward)

## Done and committed
- ingest/constants.py: GitHub client block — GITHUB_API_ROOT, DIFF_MEDIA_TYPE,
  PER_PAGE=100, LIST_STATE='all', LIST_SORT='created', LIST_DIRECTION='asc',
  INTER_REQUEST_DELAY_S=0.75, RATE_LIMIT_FLOOR=100, MAX_BACKOFF_ATTEMPTS=5,
  REPO_ROOT-anchored CACHE_ROOT, GHOST_AUTHOR, and the fifth reason literal
  REASON_DIFF_UNAVAILABLE='diff_unavailable'.
- ingest/github_client.py: GitHubClient, DiffUnavailable, _request() (backoff
  on 403/429, honours Retry-After), _respect_rate_limit(), _parse_ts(),
  from_list_item() -> PRMeta, _cache_path(), _read_cached_page(),
  _fetch_list_page(), iter_list_pages(), iter_pr_meta(), fetch_diff().
- Contract enforced by import direction: github_client imports
  corpus_filter.PRMeta, never the reverse.
- Cache write precedes every parse; both fetchers read back from disk.
- ingest/corpus_filter.py: author_type restored to PRMeta position 4;
  group_duplicates sort key and apply_corpus_filter keeper reference fixed.
- pyproject.toml: pytest pythonpath = ["."]. Bare `pytest` works.
- GOLDEN ASSERTION GREEN: page 1 = #16 (2013-07-02) -> #335 (2014-08-22),
  ascending, tz-aware UTC. D-P2-6 confirmed on real data.
- CACHE-READ PATH GREEN: second smoke run served 100 items from
  .cache/prs/ with no httpx request logged.
- test_corpus_filter.py green, Counter printed and READ:
  {None: 3, bot_author: 2, duplicate_resubmission: 2, housekeeping: 1}.
  Run it with -s or pytest swallows the print.

## Deployed state
- Unchanged. Not deployed (Cloud Run is Phase 7 per 04 §9). Skeleton 433 MB.
- Neon: schema v001, 6 tables, empty. Migration 002 (judgments.self_authored)
  still unwritten — needed before Phase 5.
- pgvector 0.8.0 Neon / 0.8.5 local docker (D-P1-3).
- .cache/prs/ holds page 1 of processing/p5.js. .gitignore confirmed covering
  it (git status clean with the page on disk).

## Read before writing diff_parser.py
- additions and deletions are NOT in the /pulls list payload — only on
  GET /pulls/{n}. Derive both, and files_changed, from the parsed diff at
  04 §5 step 4. Do not reach for a re-fetch.
- diff_unavailable is applied at step 3 by catching DiffUnavailable. NOT the
  parser's job, and NOT no_source_content: 406 means too much content,
  4b means none.
- CACHE COLLISION, STILL UNVERIFIED: .cache/diffs/<number>.diff has no repo
  namespace, but 02 §9 keeps the Day-4 FastAPI diffs in .cache/. #8862 exists
  in both repos. CHECK what spikes/day4_*.py wrote BEFORE any diff fetching.
- BOT_ACCOUNTS is matched exactly, but real bot logins carry a '[bot]' suffix.
  9001 passes only because author_type=='Bot' catches it first. A suffixed
  login that GitHub reports as 'User' slips both rules. The first full fetch's
  exclusion counts will show whether this is real — fold into D-P2-5's log.

## Open decisions carried forward
- D-P2-4 OPEN: "near-identical title" (normalized-exact OR ratio >= 0.95;
  7-day window anchored to the group's first member). Resolve from the logged
  duplicate groups after the first full list fetch.
- D-P2-5 OPEN: housekeeping patterns case-sensitive per 01 §2; case-only
  near-misses logged, not matched. Resolve from the same log.
- D-P3-1 OPEN: manual ::vector cast vs pgvector asyncpg codec. Phase 3.
- D-P3-2 OPEN: Neon pooled + asyncpg create_pool() under Cloud Run churn.
  Phase 7. statement_cache_size=0 is the known fallback.
- D-P5-2 OPEN: 01 §7 anchors and §8 subsystems carry STALE markers.
  Rewrite before Day 25.

## Carried-over obligations
- tests/test_github_client.py NOT written — deferred yesterday when PRMeta
  was about to change. PRMeta is now stable. Write it: from_list_item over
  two saved fixture items, one with "user": null asserting author == 'ghost'.
- 01 §7 anchor rewrite: diffs for #8862, #8964, #8823 — now a fetch_diff()
  call. Plus p5.js /labels confirmed against the actual page.
- #8862 truncates hard: 2 of 3 source hunks over 256 tokens, range 64-614,
  median 387. Any anchor written against it says so.
- README at Phase 9 owes FIVE exclusion counts, not four.
- Migration 002 for judgments.self_authored.
- 04 §5 needs a step 3b line for diff_unavailable in the doc revision pass.
- Reserved (CodeDay), Good First Issue, Help Wanted: process labels, NOT
  exclusions.
- MAX vs mean-of-top-3: Day-4 evidence exists (p5.js Similar B full-diff
  winner was shared test scaffolding, 0.6788 -> 0.7074). Re-examine at
  Milestone A. D-P2-2 leans on the same evidence.

## Decisions log watermark
- Current through D-P2-7, committed. D-P2-2, D-P2-6, D-P2-7 all RESOLVED.
  D-P5-2 remains the highest-numbered Phase 5 entry.

## Next session starts with
- Day 8: write tests/test_github_client.py first (~20 min, PRMeta is stable
  now, and it is the one thing 07 §3 owes for the stage built yesterday).
- Then the full list fetch on processing/p5.js: ~44 pages under state=all,
  ~1% of quota, pages 2+ hit the network, page 1 comes from cache.
- Pipe it through apply_corpus_filter(). First contact with real data.
  Print the exclusion_reason Counter and READ it. Expect four reasons, not
  five — diff_unavailable cannot appear until step 3.
- Read the logged duplicate groups and housekeeping near-misses: that closes
  D-P2-4 and D-P2-5, and answers the BOT_ACCOUNTS suffix question.