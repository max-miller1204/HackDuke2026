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
