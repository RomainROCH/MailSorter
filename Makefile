# Simple helpers for local development
.PHONY: install venv test lint format docker-build benchmark benchmark-quick benchmark-all package package-release clean-dist

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
# Packaging targets
# ============================================================================

# Package extension as XPI (uses version from manifest.json)
package:
	@echo "Packaging extension..."
	@python scripts/package_xpi.py

# Package with specific version and update version files
package-release:
	@echo "Creating release package..."
	@python scripts/package_xpi.py --update-version --version $(VERSION)

# Validate extension without packaging
package-validate:
	@python scripts/package_xpi.py --validate-only

# Clean dist folder
clean-dist:
	@echo "Cleaning dist folder..."
	@if exist dist rmdir /s /q dist
	@echo "Done."

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
