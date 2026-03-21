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

## Work Units

### Dependency Analysis

The spec modifies two files: `scripts/quant_models.py` and `final_four_analysis.ipynb`. The notebook cells import and call the classes defined in the Python module, creating a strict dependency: the Python module changes must land first.

Within `quant_models.py`, `EVOptimizedSimulator` takes a `public_ownership` instance in its constructor, so `PublicOwnership` must exist before `EVOptimizedSimulator` can be used. However, both classes can be written in the same file simultaneously since the dependency is at instantiation time, not at Python definition time.

### Unit 1 — Foundation: Python Classes (scripts/quant_models.py)

**Must complete before Unit 2.**

| Attribute | Detail |
|---|---|
| Files owned | `scripts/quant_models.py` |
| Scope | Add `PublicOwnership` class after `HistoricalPrior`; add `EVOptimizedSimulator` class after `PublicOwnership` |
| Estimated size | ~240 lines of new code |
| Dependencies | None — builds on classes already in the file (`HistoricalPrior`, `QuantEnhancedSimulator`) |
| Done when | Both classes are defined, importable, and pass a smoke import test (`from scripts.quant_models import PublicOwnership, EVOptimizedSimulator`) |

Key implementation notes:
- `PublicOwnership` is self-contained (hardcoded data + one method). No external dependencies.
- `EVOptimizedSimulator` references the existing `_win_prob` pattern from `QuantEnhancedSimulator` for its `_win_prob_no_prior` method. Read that method before writing.
- Insert both classes between `HistoricalPrior` and the existing `QuantEnhancedSimulator` class to keep logical ordering.

### Unit 2 — Parallel-ready after Unit 1: Notebook Section 10 (final_four_analysis.ipynb)

**Depends on Unit 1 being complete.**

| Attribute | Detail |
|---|---|
| Files owned | `final_four_analysis.ipynb` |
| Scope | Update existing import cell to include new classes; append 9 new cells as Section 10 |
| Estimated size | 9 new cells (mix of code and markdown) |
| Dependencies | Unit 1 (imports `PublicOwnership` and `EVOptimizedSimulator` from `quant_models`) |
| Done when | Notebook runs end-to-end; Section 10 produces a 63-game bracket with EV scores; varying `LEVERAGE_WEIGHT` changes output picks |

Key implementation notes:
- Cell 1 modifies an existing import cell — coordinate carefully to avoid merge conflicts with any other notebook changes.
- Cells 4-9 are display/visualization cells with no cross-dependencies and could theoretically be authored in any order.
- The notebook also depends on runtime artifacts from earlier cells (bracket_df, kenpom_df, fitted GARCH/HMM/Kalman objects), so end-to-end verification requires running the full notebook.

### Execution Plan

```
Unit 1 (quant_models.py)
        |
        v
Unit 2 (final_four_analysis.ipynb)
```

There are only two files and a strict sequential dependency between them, so **no parallelism is possible for this spec**. Unit 1 must fully complete before Unit 2 begins, because Unit 2 imports symbols that Unit 1 creates. Running them in separate worktrees would cause import failures during development of Unit 2.

If the scope were larger (e.g., multiple independent Python modules or independent notebook sections), units could run in parallel. Here, the minimal decomposition is two sequential units with exclusive file ownership.
