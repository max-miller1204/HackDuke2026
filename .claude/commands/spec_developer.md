Read $1 and interview me in detail using the AskUserQuestionTool about literally anything:
- Technical implementation
- UI & UX
- Concerns
- Tradeoffs, etc.

But make sure the questions are not obvious

Be very in-depth and continue interviewing me continually until it's complete, then write the spec to the file.

---

## Work Unit Structuring (REQUIRED after spec is complete)

After writing the full spec, you MUST add a **Work Units** section at the end. This section enables parallel execution — without it, the spec can't be used by `/bootstrap` or dispatched to parallel agents.

### How to structure work units

1. **Identify the foundation** — Look at the spec's deliverables and find work that everything else depends on:
   - Shared types, interfaces, schemas, or data models
   - Project scaffolding (folder structure, configs, package manifests)
   - Shared utilities or helpers that multiple features import
   - Database schemas or migrations
   - Base classes or core abstractions

   The foundation is **project-type-dependent** — infer it from the spec's tech stack and deliverables:
   - Python data/analysis: `requirements.txt`, shared utilities, data schemas, base classes
   - Web app (Next.js, React, etc.): `package.json`, project scaffold, shared types, DB schema, auth setup
   - API service: project scaffold, shared types/models, middleware, DB setup
   - Monorepo: root configs, shared packages, workspace setup

   If nothing qualifies as foundation (all units are truly independent), skip it — mark all units as parallel.

2. **Group remaining work into parallel units** — Each unit must:
   - Own its files exclusively (no file touched by two units)
   - Be independently testable
   - Depend only on foundation work, not on other parallel units
   - Have **no runtime/import dependencies** on other parallel units (e.g., if Unit B imports a class that Unit A creates, they cannot be parallel)

3. **Analyze dependencies** — Check for TWO types of conflicts:

   **a. File conflicts:** Verify each file appears in at most one unit. If a file must be touched by multiple units, either:
   - Move it to the foundation phase
   - Restructure units so one unit owns that file

   **b. Runtime/import dependencies:** Check if any unit imports from, calls into, or depends on output from another unit. Common patterns:
   - Unit B imports a class/function that Unit A creates → NOT parallelizable
   - Unit B reads a file that Unit A generates → NOT parallelizable
   - Unit B's tests require Unit A's code to exist → NOT parallelizable

   If runtime dependencies exist between units, you have three options:
   - **Merge dependent units** into a single sequential unit
   - **Move the depended-on work to foundation** so it's done before all parallel units
   - **Chain the units** as sequential phases (Phase 2a → Phase 2b) rather than parallel

4. **Determine execution strategy** — Based on the analysis:
   - **All units independent:** Foundation → Parallel units (concurrent worktrees)
   - **Some units have dependencies:** Foundation → Independent parallel units + Sequential dependent units
   - **All units are tightly coupled:** Foundation → Sequential execution (single worker, no parallelism). This is fine — not everything benefits from parallel agents. Say so explicitly.

### Output format

Add this section at the end of the spec:

```markdown
---

## Work Units

### Execution Strategy
[One of: "Foundation → Parallel (concurrent worktrees)", "Foundation → Mixed (parallel + sequential)", or "Sequential (single worker)"]

**Rationale:** [Why this strategy — what dependencies exist or don't]

### Foundation Unit (Phase 1)
> Skip this section if no foundation work is needed.

**Files:**
- Create: `path/to/file`
- Modify: `path/to/existing`

**Tasks:**
- [description of each foundation task]

**Done when:** [how to verify foundation is complete before moving to Phase 2]

### Parallel Units (Phase 2)
> Skip this section if execution strategy is "Sequential"

| # | Unit Name | Files (create/modify) | Description | E2E Test |
|---|-----------|----------------------|-------------|----------|
| 1 | ... | ... | ... | ... |
| 2 | ... | ... | ... | ... |

### Sequential Units
> Only include if some units have runtime/import dependencies that prevent parallel execution.

| Order | Unit Name | Files (create/modify) | Depends On | Description |
|-------|-----------|----------------------|------------|-------------|
| 1 | ... | ... | Foundation | ... |
| 2 | ... | ... | Unit 1 (imports X) | ... |

### Dependency & Conflict Analysis
- **File conflicts:** [Confirm no file is touched by more than one parallel unit, or explain resolution]
- **Runtime dependencies:** [List any import/call/output dependencies between units. If none, say "None — all units are independently executable"]

### Post-Merge Verification
[E2E test recipe that requires all units merged — run after everything is integrated.]
```

This structure is what `/bootstrap` consumes to dispatch foundation work first, then parallel agents with worktrees for each unit.
