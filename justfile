default: lint-all

mypy:
    uv run mypy --sqlite-cache

format:
    uv run ruff format

lint:
    uv run ruff check

lint-all: format lint mypy

setup:
    chmod +x scripts/setup.sh
    scripts/setup.sh