#!/usr/bin/env bash
set -euo pipefail

if ! command -v poetry >/dev/null 2>&1; then
  echo "Poetry not found — install it first: https://python-poetry.org/docs/#installation"
  exit 1
fi

echo "Installing project dependencies with poetry..."
poetry install

echo "To activate the venv run: 'poetry shell' or 'poetry run <cmd>'"
