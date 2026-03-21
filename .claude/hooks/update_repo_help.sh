#!/bin/bash
# PostToolUse hook: detect changes to .claude/ config files and remind to update repo-claude-help.md
# Reads tool_input from stdin JSON to get the file path that was just written/edited

FILE_PATH=$(jq -r '.tool_input.file_path // .tool_response.filePath // ""' 2>/dev/null)

# Only trigger for changes to .claude/ skills, hooks, agents, commands, or settings
if echo "$FILE_PATH" | grep -qE '\.claude/(skills|hooks|agents|commands|settings)'; then
    # Don't trigger if we're already updating the help file
    if echo "$FILE_PATH" | grep -q 'repo-claude-help'; then
        exit 0
    fi
    printf '{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "A Claude config file was just modified (%s). Update repo-claude-help.md if this change affects the documented skills, hooks, agents, or settings."}}\n' "$FILE_PATH"
fi
