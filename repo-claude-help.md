# Claude Code Reference for This Repo

## Skills (invoke with `/skill-name`)

### `/scrape` — Web Scraping
Scrape tabular data from a sports analytics website and save as CSV to `scraped_data/`.

**Usage:** `/scrape <url> <description of what data to extract>`

**Workflow:** Fetches page → writes a Python scraper in `scripts/` → runs it → validates output → runs data-reviewer agent on the CSV.

**Allowed domains** are configured in `.claude/settings.local.json`.

---

### `/todo` — Todo Manager
Manage prioritized todo files in `todo/` with dependency-aware ordering.

| Command | What it does |
|---------|-------------|
| `/todo` | List all todos in priority order |
| `/todo add <description>` | Add a new todo, auto-placed by dependencies |
| `/todo done <number>` | Complete a todo (moves to `todo/done/`) |
| `/todo reprioritize` | Reorder all todos based on dependencies |

---

### `/spec_developer` — Spec Interview
**MAKE SURE YOU'RE IN PLAN MODE WHEN RUNNING**. Reads a file and interviews you in detail about technical implementation, UI/UX, concerns, and tradeoffs. Writes the spec when the interview is complete. **Includes Work Units structuring** — after writing the spec, it adds a Work Units section with dependency analysis (both file conflicts AND runtime/import dependencies), execution strategy, and unit breakdown. This makes the output directly consumable by `/bootstrap`.

**Usage:** `/spec_developer <file>`

**Execution strategies it can recommend:**
- **Foundation → Parallel** — all units are independent after foundation
- **Foundation → Mixed** — some parallel, some sequential (runtime dependencies)
- **Sequential** — tightly coupled work, single worker (e.g., notebook imports from script it depends on)

---

### `/bootstrap` — Spec Execution with Worktrees
Executes a work-unit-structured spec (from `/spec_developer` or any planning tool). Adapts execution based on the spec's declared strategy:

1. **Foundation phase** (sequential) — shared scaffolding, configs, types, schemas. Dynamically inferred from tech stack.
2. **Parallel build phase** (concurrent agents + worktrees) — independent units each get their own agent in an isolated worktree.
3. **Sequential phase** (if needed) — units with runtime/import dependencies run in order. Will tell you "no" to parallelism when dependencies prevent it.

**Usage:** `/bootstrap <spec-file>` or "bootstrap this spec"

**Requires:** A spec with a Work Units section (execution strategy + dependency analysis).

**Checkpoints:** Pauses between phases for user review. Reports agent status as they complete. Runs post-merge verification after integration.

---

### `/audit` — Algorithm Auditor
Audit the prediction engine's core algorithms for correctness risks, silent degradation, and maintenance hazards.

**Usage:** `/audit` or "audit the prediction models"

**4 Audit Phases:**
1. **Stray Variables** — unused imports, dead assignments, disconnected pipeline stages
2. **Hardcoded Bias** — magic numbers, duplicated constants (NAME_ALIASES, default volatility), undocumented scaling factors
3. **Feature Usage** — composite weight summation, NaN propagation risk, graceful degradation paths
4. **Model Consistency** — EVOptimizedSimulator vs QuantEnhancedSimulator `_win_prob()` diff, fallback equivalence, GARCH stationarity

**Output:** Structured markdown report saved to `reports/audit_YYYY-MM-DD.md` with severity-rated findings (Critical/Warning/Info) and prioritized recommendations.

---

## Agents (used by Claude automatically or via subagent dispatch)

### `data-reviewer`
Validates CSV data quality in `scraped_data/`. Checks for:
- Missing values, type consistency, duplicates
- Domain validation (ranks, scores, dates, conferences)
- Cross-file consistency (team names across files)

Outputs a structured Data Quality Report with errors/warnings.

---

## Hooks (run automatically)

### SessionStart
Both hooks fire on every session start (startup, resume, clear):

1. **Archive Plan** (`archive_plan_session_start.py`)
   - Archives the most recent plan from `past-plans/` into date-stamped subfolders
   - Prevents duplicate archives via content hashing
   - Deletes the original after archiving

2. **Todo Display** (`todo_session_start.sh`)
   - Displays current todo list as a system message at session start
   - Reads all `XX-*.md` files from `todo/` and shows them in priority order

### PostToolUse (Write|Edit)

3. **Update Repo Help** (`update_repo_help.sh`)
   - Fires after any Write or Edit to files in `.claude/`
   - Injects a reminder to update `repo-claude-help.md` if the change affects documented skills, hooks, agents, or settings
   - Ignores changes to non-config files

---

## Plugins

### superpowers (`claude-plugins-official`)
Adds many workflow skills:

| Skill | When to use |
|-------|-------------|
| `/brainstorming` | Before any creative/design work |
| `/writing-plans` | When you have a spec and need an implementation plan |
| `/executing-plans` | Execute a written plan with review checkpoints |
| `/subagent-driven-development` | Execute plans with independent parallel tasks |
| `/dispatching-parallel-agents` | 2+ independent tasks that can run in parallel |
| `/test-driven-development` | Before writing implementation code |
| `/systematic-debugging` | When encountering bugs or test failures |
| `/verification-before-completion` | Before claiming work is done |
| `/requesting-code-review` | After completing features, before merging |
| `/receiving-code-review` | When getting feedback on code |
| `/finishing-a-development-branch` | When implementation is done, deciding merge strategy |
| `/using-git-worktrees` | When feature work needs isolation |
| `/writing-skills` | Creating or editing skills |
| `/simplify` | Review changed code for quality/efficiency |
| `/update-config` | Modify settings.json (hooks, permissions, env vars) |
| `/keybindings-help` | Customize keyboard shortcuts |
| `/loop` | Run a command on a recurring interval |

### skill-creator (`claude-plugins-official`)
| Skill | When to use |
|-------|-------------|
| `/skill-creator` | Create, modify, eval, and benchmark skills |

---

## Settings Overview

**File:** `.claude/settings.json`

- **plansDirectory:** `./past-plans` — where active plans are stored
- **Hooks:** SessionStart fires archive + todo display
- **Plugins:** superpowers, skill-creator

---

## Refresh Pipeline

Live tournament data ingestion via `scripts/refresh.py`. Scrapes ESPN results, re-fits models, tracks accuracy, and archives runs.

```bash
python scripts/refresh.py all                          # Full pipeline
python scripts/refresh.py --no-notebook all            # Skip notebook re-execution
python scripts/refresh.py --tournament-weight 3.0 all  # Heavier tournament weighting
python scripts/refresh.py results                      # Scrape ESPN scores only
python scripts/refresh.py simulate                     # Re-fit models + re-simulate
python scripts/refresh.py accuracy                     # Generate accuracy dashboard
python scripts/refresh.py archive                      # Archive current outputs
python scripts/refresh.py scrape                       # Re-scrape KenPom/NET/injuries
python scripts/refresh.py watch --interval 30m         # Auto-poll every 30 minutes
```

| Module | File | Purpose |
|--------|------|---------|
| Orchestrator | `scripts/refresh.py` | CLI entry point with 7 subcommands |
| Tournament State | `scripts/refresh/tournament_state.py` | Manage `scraped_data/tournament_state.json` |
| Results Scraper | `scripts/refresh/scrape_results.py` | ESPN scoreboard scraper with retry |
| Model Re-fitter | `scripts/refresh/refit_models.py` | Re-fit GARCH/HMM/Kalman with tournament data |
| Accuracy Tracker | `scripts/refresh/accuracy.py` | Prediction tracking + 4-subplot dashboard |
| Changelog | `scripts/refresh/changelog.py` | Markdown diff generation |
| Archive | `scripts/refresh/archive.py` | Timestamped output archiving to `reports/` |
| Validator | `scripts/refresh/validator.py` | Post-scrape data quality checks |
| Scheduler | `scripts/refresh/scheduler.py` | Fixed-interval polling loop |

**Outputs:** `scraped_data/tournament_state.json`, `images/accuracy_dashboard.png`, `reports/changelog_*.md`, `reports/run_YYYY-MM-DD_HH-MM/`

---

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `todo/` | Active todo files (`XX-name.md`) |
| `todo/done/` | Completed todos |
| `scraped_data/` | CSV files from scraping |
| `scripts/` | Python scraper scripts |
| `scripts/refresh/` | Refresh pipeline modules |
| `reports/` | Timestamped run archives and changelogs |
| `past-plans/` | Active plans (archived into date subfolders) |
| `.claude/skills/` | Custom skill definitions |
| `.claude/hooks/` | Hook scripts |
| `.claude/agents/` | Custom agent definitions |
| `.claude/commands/` | Custom slash commands |
