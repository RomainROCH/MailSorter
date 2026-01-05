#!/usr/bin/env bash
set -euo pipefail

cd /mnt/e/MailSorter
branches=(feat/ci-lint feat/release-workflow fix/lint-errors chore/dev-environment chore/autoformat-lint)

for b in "${branches[@]}"; do
  echo -e "\n=== Processing $b ==="
  git fetch origin "$b" || true
  if git rev-parse --verify "origin/$b" >/dev/null 2>&1; then
    git checkout "$b" || git checkout -b "$b" "origin/$b" || true
  else
    git checkout "$b" || true
  fi

  echo "Running Docker formatter for $b..."
  docker run --rm -v /mnt/e/MailSorter:/src -w /src python:3.10-slim bash -lc 'pip install --no-cache-dir black ruff && black . && ruff check --fix .' || true

  if [ -n "$(git status --porcelain)" ]; then
    git add -A
    if git commit -m "chore: apply formatting fixes (black/ruff)"; then
      git push origin "$b" || echo "Push failed for $b"
    else
      echo "Nothing to commit for $b"
    fi
  else
    echo "No formatting changes for $b"
  fi

done

git checkout main
