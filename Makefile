# Simple helpers for local development
.PHONY: install venv test lint format docker-build benchmark benchmark-quick benchmark-all

install:
	@poetry install

venv:
	@poetry install

test:
	@poetry run pytest -q

lint:
	@poetry run ruff check .
	@poetry run black --check .
	@poetry run mypy backend

format:
	@poetry run black .
	@poetry run ruff check --fix .

docker-build:
	@docker build -t mail-sorter:latest .

# ============================================================================
# Benchmark targets
# ============================================================================

# Quick sanity check on available providers
benchmark-quick:
	@echo "Running quick benchmark..."
	@poetry run python -m benchmarks.quick_test

# Full benchmark on Ollama only (default, free)
benchmark:
	@echo "Running benchmark on Ollama..."
	@poetry run python -m benchmarks.runner --providers ollama --verbose

# Full benchmark on all configured providers (may incur costs)
benchmark-all:
	@echo "Running benchmark on ALL providers (may incur API costs)..."
	@poetry run python -m benchmarks.runner --all --verbose

# Compare Ollama vs cloud providers
benchmark-compare:
	@echo "Running comparison benchmark..."
	@poetry run python -m benchmarks.runner --providers ollama openai anthropic gemini --verbose
