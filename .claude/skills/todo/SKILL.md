---
name: todo
description: Manage prioritized todo files in todo/ — list, add, complete, and reprioritize tasks with dependency-aware ordering
---

# Todo Manager

Manage todo files in `todo/` with dependency-aware prioritization.

## Usage

- `/todo` — list all todos in priority order
- `/todo add <description>` — add a new todo, auto-placed by dependencies
- `/todo done <number>` — mark a todo as complete (moves to `todo/done/`)
- `/todo reprioritize` — reorder all todos based on dependencies

## Commands

### List: `/todo` (no arguments)

1. Read all files in `todo/` matching `XX-*.md`
2. Sort by number prefix
3. Display each todo as: `XX. <name> — <first line of content>`

### Add: `/todo add <description>`

1. Read the description from `$ARGUMENTS`
2. Read all existing todo files in `todo/` to understand their content
3. Generate a kebab-case filename from the description
4. Analyze dependencies: determine where this new task fits relative to existing tasks
   - Which existing tasks must be done before this one?
   - Which existing tasks depend on this one?
5. Insert the new todo at the correct position
6. Renumber ALL files in `todo/` to maintain sequential `XX-` prefixes (zero-padded)
7. Write the description as the content of the new `.md` file
8. Display the updated todo list

### Done: `/todo done <number>`

1. Find the file in `todo/` with the matching number prefix (e.g., `02-*.md`)
2. Create `todo/done/` directory if it doesn't exist
3. Move the file to `todo/done/`
4. Renumber remaining files in `todo/` to fill the gap
5. Display the updated todo list

### Reprioritize: `/todo reprioritize`

1. Read the content of every `XX-*.md` file in `todo/`
2. Analyze dependency relationships between all tasks:
   - Which tasks are prerequisites for others?
   - Which tasks are independent?
   - Independent tasks retain their relative order
3. Determine the correct dependency-respecting order
4. Renumber and rename all files to reflect the new order
5. Display the reordered list and explain what changed

## File Renaming

When renumbering files, rename them using the Bash tool with `mv`:
```
mv todo/03-old-name.md todo/01-old-name.md
```

Always use zero-padded two-digit prefixes (01, 02, ... 99).

## Arguments

- `$ARGUMENTS`: The subcommand and its arguments (e.g., `add Fix the login bug`, `done 3`, `reprioritize`)
