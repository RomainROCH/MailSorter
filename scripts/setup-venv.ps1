#!/usr/bin/env pwsh
if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
  Write-Host "Poetry not found — install it first: https://python-poetry.org/docs/#installation"; exit 1
}
Write-Host "Installing project dependencies with poetry..."
poetry install
Write-Host "To activate the venv run: 'poetry shell' or 'poetry run <cmd>'"
