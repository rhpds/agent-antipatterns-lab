#!/bin/bash
# Setup script for .claude/settings.json hooks

set -e

TEMPLATE_FILE=".claude.settings.template.json"
TARGET_FILE=".claude/settings.json"

if [ ! -f "$TEMPLATE_FILE" ]; then
  echo "ERROR: $TEMPLATE_FILE not found"
  exit 1
fi

if [ -f "$TARGET_FILE" ]; then
  echo "$TARGET_FILE already exists"
  echo "  To update, run: cp $TEMPLATE_FILE $TARGET_FILE"
  exit 0
fi

mkdir -p .claude
cp "$TEMPLATE_FILE" "$TARGET_FILE"

echo "Created $TARGET_FILE from template"

if jq empty "$TARGET_FILE" 2>/dev/null; then
  echo "JSON validation passed"
else
  echo "JSON validation failed"
  exit 1
fi

exit 0
