# Simple helpers for local development
.PHONY: install venv test lint format docker-build

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
