# Spec: EV-Optimized Bracket Extension

## Context
Add an unconstrained EV-optimized bracket section to the existing notebook. This adds new classes to the existing quant_models.py module and new cells to the notebook that import and use those classes.

## Deliverables

1. **`scripts/quant_models.py`** (modify) — Add `PublicOwnership` class (~40 lines) and `EVOptimizedSimulator` class (~200 lines)
2. **`final_four_analysis.ipynb`** (modify) — Update import cell, add 9 new cells as Section 10 that instantiate and run `EVOptimizedSimulator`

## Implementation Details

### PublicOwnership class (in quant_models.py)
- Hardcoded ESPN-calibrated ownership table by (seed, round)
- `get_ownership(seed, round_index)` method
- Insert after existing `HistoricalPrior` class

### EVOptimizedSimulator class (in quant_models.py)
- Constructor takes bracket_df, kenpom_df, garch, hmm, kalman, public_ownership
- `_win_prob_no_prior()` — copy of existing `_win_prob` without prior blending
- `run()` — 3-phase: simulate 50K brackets, compute per-slot EV, leverage-weighted picks
- Returns bracket_picks, ev_scores, leverage_data, champion, ff_probs

### Notebook Section 10 (in final_four_analysis.ipynb)
- Cell 1: Import `PublicOwnership, EVOptimizedSimulator` from quant_models
- Cell 2: Setup with configurable LEVERAGE_WEIGHT
- Cell 3: Run EV simulation
- Cells 4-9: Display results, comparisons, visualizations

## Verification
1. Run full notebook end-to-end
2. New section produces 63-game bracket with EV scores
3. Changing LEVERAGE_WEIGHT shifts picks

---

## Work Units

### Execution Strategy
Sequential (single worker)

**Rationale:** The notebook (`final_four_analysis.ipynb`) directly imports `PublicOwnership` and `EVOptimizedSimulator` from `scripts/quant_models.py`. This is a hard runtime/import dependency — the notebook cells cannot execute, be tested, or even parse correctly without the classes existing in quant_models.py first. Since there are only two deliverables and one depends on the other, parallel execution provides no benefit. A single worker executing sequentially is the correct strategy.

### Sequential Units

| Order | Unit Name | Files (create/modify) | Depends On | Description |
|-------|-----------|----------------------|------------|-------------|
| 1 | Quant Models Extension | Modify: `scripts/quant_models.py` | Foundation (existing codebase) | Add `PublicOwnership` class with ESPN-calibrated ownership table and `get_ownership()` method. Add `EVOptimizedSimulator` class with constructor, `_win_prob_no_prior()`, and `run()` method implementing 3-phase EV simulation. Insert both after existing `HistoricalPrior` class. |
| 2 | Notebook EV Section | Modify: `final_four_analysis.ipynb` | Unit 1 (imports `PublicOwnership`, `EVOptimizedSimulator` from `quant_models`) | Update the existing import cell to include new classes. Add 9 new cells as Section 10: instantiation, EV simulation execution, results display, comparisons, and visualizations. |

### Dependency & Conflict Analysis
- **File conflicts:** None — each unit modifies exactly one file (`scripts/quant_models.py` and `final_four_analysis.ipynb` respectively), with no overlap.
- **Runtime dependencies:** Unit 2 imports `PublicOwnership` and `EVOptimizedSimulator` from `scripts/quant_models.py`, which are created by Unit 1. Unit 2 cannot be executed or tested until Unit 1 is complete. This is a hard import dependency that prevents parallel execution.

### Post-Merge Verification
Run the full notebook end-to-end (`jupyter nbconvert --execute final_four_analysis.ipynb` or run all cells interactively). Verify that:
1. Section 10 executes without import errors
2. A 63-game bracket with EV scores is produced
3. Changing `LEVERAGE_WEIGHT` in the setup cell and re-running produces different pick selections
