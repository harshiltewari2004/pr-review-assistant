# Handoff — Day 27 close

## State
- HEAD: <hash after ledger commit> on `main`, pushed, clean tree
- Tests: 72 passed, 1 skipped (`pytest -q`)
- ruff check / format clean
- 23 sessions remain. ⚠️ Day-26 estimate was 28–32 sessions of work —
  reconcile against `09` cut order before Phase 5.

## Gate
```bash
cd ~/pr-review-assistant && source .venv/bin/activate
set -a && source .env && set +a
docker compose up -d
git status --porcelain
ruff check && ruff format --check .
pytest -q
python -m scripts.day27_orchestrator_spike
```
Expected: clean tree, 72/1, and the spike prints |C|=143 and golden PASS.

## ✅ Invariant 2 now held in running code
find_similar_prs() in scoring.py: nominate → union → full backfill → rank.
D-P4-13 (full vector backfill), D-P4-10 resolved locally.

## 🎯 NEXT SESSION — fixed order
1. Doc 12 ritual: normalize.py + scoring.py (combined). Due within 2 days.
2. Schedule reconciliation vs `09` cut order.
3. Phase 5 entry.

## Owed / doc-revision batch (additions today)
- Test docstrings: `query` does NOT catch a missing id clause while `<`
  is strict — reword in test_retrieval.py and test_signals.py
- `bm25_signal()` has no production call site (orchestrator uses
  bm25_scores) — reference-location pattern #5
- `<$3` spacing on signals.py L207, L240
- 04 §10 JSON log formatter doesn't exist — every script drops `extra`
- /analyze: no query_pr_id for a new PR; query_created_at = now (Phase 7)
- Garbles in scoring.py docstrings: `teh`, `MEMEBERSHIP`, `memberships`,
  `Nominate ,union`, `candidates.id over nowhere`
- (all prior items still owed)