#!/usr/bin/env bash
# PreToolUse hook — blocks non-PH tools from being used in project repos.
# Stage gating is handled by the orchestrator skill via the Central API.

TOOL="${CLAUDE_TOOL_NAME:-${TOOL_NAME:-}}"

[[ -z "$TOOL" ]] && exit 0

BLOCKED="reporting.db.prod|mcp__reporting|ph_rcars_query"
if echo "$TOOL" | grep -qiE "$BLOCKED"; then
  echo "[PH Hook] BLOCKED: '$TOOL' is not permitted in Publishing House projects." >&2
  exit 2
fi

exit 0
