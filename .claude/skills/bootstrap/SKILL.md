---
name: bootstrap
description: Execute a spec with work units — foundation phase first, then parallel agents with worktrees. Use when you have a spec (from spec_developer or any planning tool) that contains a Work Units section and you want to build it out. Works for greenfield projects and feature additions. Trigger when the user says "bootstrap this", "build this spec", "execute this plan with worktrees", or references a spec file they want built.
---

# Bootstrap

Execute a work-unit-structured spec in two phases: **foundation first** (sequential, single agent), then **parallel build** (independent agents, each in its own worktree). Designed for both greenfield projects and feature additions where scope is broad enough that a single agent loses context or runs out of steam.

**Announce at start:** "I'm using the bootstrap skill to execute this spec."

## Prerequisites

The spec MUST have a **Work Units** section with:
- Execution strategy (one of: "Foundation → Parallel", "Foundation → Mixed", or "Sequential")
- Foundation unit (optional — skip if all units are independent)
- Parallel units table and/or sequential units table
- Dependency & conflict analysis

If the spec lacks this structure, tell the user: "This spec doesn't have work units defined. Run `/spec_developer` first — it will structure the output for parallel execution."

## Step 0: Load and Validate the Spec

1. Read the spec file the user provides
2. Verify the Work Units section exists and is well-formed
3. Identify:
   - **Foundation tasks** — what must be done before parallel work begins
   - **Parallel units** — independent work that can be dispatched concurrently
   - **Tech stack** — inferred from spec (determines foundation approach)
   - **Post-merge verification** — the E2E test recipe for after everything merges

4. Present a summary to the user:

```
Spec: [name]
Execution strategy: [strategy from spec]
Foundation: [brief description of foundation work, or "None — all units are independent"]
Parallel units: [count] units
  1. [unit name] — [files]
Sequential units: [count] units (runtime dependencies prevent parallelism)
  1. [unit name] — depends on [what]
Post-merge test: [brief description]

Ready to start? [description of execution plan based on strategy]
```

Wait for user confirmation before proceeding.

## Phase 1: Foundation (Sequential)

> Skip entirely if the spec has no foundation unit.

The foundation phase sets up everything that parallel units depend on. What "foundation" means depends on the project — the spec's Work Units section defines it explicitly.

**Examples of foundation work by project type** (for reference, not prescription — always follow the spec):
- **Python data/analysis**: virtual env, requirements.txt, shared utilities, data schemas
- **Web app**: scaffold (Next.js/Vite/etc.), package.json, shared types, DB schema + migrations, auth skeleton
- **API service**: project structure, shared models/types, middleware, DB setup, config management
- **Monorepo**: root configs, shared packages, workspace linking

### Execution

1. Create a feature branch: `git checkout -b bootstrap/<feature-name>`
2. Execute foundation tasks inline (no subagent needed — you have full context from the spec)
3. After each task, verify it works:
   - Files created/modified as expected
   - Dependencies install cleanly
   - Any "done when" criteria from the spec are met
4. Commit foundation work: `git add <specific files> && git commit -m "bootstrap: foundation — <description>"`
5. Tell the user what was done and ask for a quick review before Phase 2

```
Foundation complete:
- [what was created/configured]
- [verification results]

Review the foundation before I dispatch parallel agents? Or proceed directly?
```

## Phase 2: Parallel Build (Concurrent Agents + Worktrees)

Each parallel unit gets its own agent running in an isolated worktree. This means:
- No merge conflicts during development (each agent owns its files exclusively)
- No context pollution between agents
- Agents can work concurrently without coordination

### Dispatching Agents

For each parallel unit, dispatch an Agent with `isolation: "worktree"`:

**Agent prompt template:**

```
You are building one unit of a larger project. Your unit is independent — focus only on your assigned files.

## Your Unit
Name: [unit name]
Description: [from spec]

## Files You Own
- Create: [list]
- Modify: [list]

## Full Spec Context
[Paste the FULL spec text for this unit — do NOT make the agent read a file]

## Foundation Already Done
The following foundation work is already committed on the branch:
[List what was done in Phase 1 — files, packages installed, shared types available]

## Instructions
1. Implement everything described in your unit spec
2. Follow existing project conventions (check neighboring files for patterns)
3. Run the unit's E2E test if one is specified: [test command]
4. When done:
   - Commit all changes with a clear message
   - Report status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
   - If BLOCKED or NEEDS_CONTEXT, explain what you need

## Constraints
- Only touch files listed in "Files You Own" — nothing else
- Do not modify foundation files
- Do not install additional dependencies without noting it in your report
```

### Dispatch all units in a single message

Launch all parallel agents in one turn so they run concurrently. Do NOT dispatch them one at a time.

### Monitor and Report

As agents complete, collect their results. Present a summary:

```
## Parallel Build Results

| # | Unit | Status | Notes |
|---|------|--------|-------|
| 1 | [name] | DONE | [any concerns] |
| 2 | [name] | DONE_WITH_CONCERNS | [what they flagged] |
| 3 | [name] | BLOCKED | [what they need] |

[For any BLOCKED or NEEDS_CONTEXT units, explain the issue and ask the user how to proceed]
```

### Handle blocked agents

If an agent reports BLOCKED or NEEDS_CONTEXT:
1. Present the issue to the user
2. After getting guidance, dispatch a new agent for just that unit with the additional context
3. Do NOT re-run units that completed successfully

## Phase 2b: Sequential Units (if applicable)

> Skip if the execution strategy is purely parallel or if no sequential units exist.

Some units have runtime/import dependencies that prevent parallel execution — Unit B imports from Unit A, or Unit B reads output that Unit A generates. These must run in order.

### When this phase applies

- **"Foundation → Mixed" strategy:** Run parallel units first (Phase 2), then sequential units in dependency order
- **"Sequential" strategy:** Skip Phase 2 entirely. Run all units sequentially in a single worktree (or inline)

### Execution

For each sequential unit, in dependency order:

1. Execute inline or dispatch a single agent (worktree is fine for isolation, but only one at a time)
2. Verify the unit's output/exports exist before starting the next unit
3. Commit after each unit completes

Present progress after each sequential unit:

```
Sequential unit [N/total]: [name] — DONE
  Dependencies satisfied: [what this unit needed from previous units]
  Produced: [what this unit created that later units need]
```

### Why not force everything into parallel?

It's tempting to restructure specs to maximize parallelism, but some work is genuinely sequential. Two classes in the same file where one imports the other, a notebook that imports from a script — these are real dependencies, not spec problems. The skill should respect them rather than contort the architecture to enable worktrees.

## Phase 3: Integration and Verification

After all parallel units complete successfully:

1. **Verify all worktree changes merged cleanly** — the Agent tool with `isolation: "worktree"` handles this, but confirm no conflicts
2. **Run post-merge verification** from the spec's "Post-Merge Verification" section
3. **Report results:**

```
## Integration Complete

All [N] units merged. Post-merge verification:
- [test results]
- [any issues found]

Next steps:
1. Review the full diff: `git diff main...HEAD`
2. Commit/push when ready
3. Create a PR, merge locally, or keep the branch as-is
```

## Important Rules

- **Never skip the user checkpoint** between Phase 1 and Phase 2. The user wants to stay hands-on.
- **Never dispatch parallel agents without confirming** the foundation is solid first.
- **Always paste full spec text** into agent prompts — never make agents read files for their task description.
- **File ownership is sacred** — if two units need the same file, that's a spec problem. Surface it to the user rather than hacking around it.
- **Graceful degradation** — if only 1 parallel unit exists, just run it inline instead of dispatching an agent. The overhead isn't worth it for a single unit.
- **Report agent durations** — when agents complete, note how long each took so the user can gauge the process.
