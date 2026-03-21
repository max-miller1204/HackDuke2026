#!/bin/bash
# Display current todo list at session start
TODO_DIR="${CLAUDE_PROJECT_DIR}/todo"
if [ -d "$TODO_DIR" ]; then
    files=$(ls "$TODO_DIR"/[0-9][0-9]-*.md 2>/dev/null | sort)
    if [ -n "$files" ]; then
        msg="\n=== Current TODOs ===\n"
        for f in $files; do
            name=$(basename "$f" .md)
            num="${name%%-*}"
            title="${name#*-}"
            title=$(echo "$title" | tr '-' ' ')
            first_line=$(head -1 "$f" 2>/dev/null | sed 's/"/\\"/g')
            msg+="  ${num}. ${title} — ${first_line}\n"
        done
        msg+="===================="
        printf '{"systemMessage": "%s"}\n' "$msg"
    fi
fi
