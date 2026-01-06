#!/usr/bin/env bash
set -euo pipefail

# Simple secret-like file detector for PRs
patterns=("secrets.json" ".pem" ".key" ".sqlite3" "local_settings.py" ".env" ".env.local")

# Try to fetch origin/main for a reliable diff; ignore errors
git fetch origin main:main 2>/dev/null || true

changed_files=$(git diff --name-only origin/main...HEAD || git ls-files)
matches=()
for p in "${patterns[@]}"; do
  while IFS= read -r f; do
    if [[ "$f" == *"$p"* ]]; then
      matches+=("$f")
    fi
  done <<< "$changed_files"
done

if [ ${#matches[@]} -ne 0 ]; then
  echo "Secret-like files detected in this PR:" >&2
  for m in "${matches[@]}"; do echo " - $m" >&2; done
  echo "Please remove or move these files and ensure secrets are stored securely (e.g., secrets manager)." >&2
  exit 1
fi

echo "No secret-like files found."
