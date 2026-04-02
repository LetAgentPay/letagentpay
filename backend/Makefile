.PHONY: help install install-dev format lint test test-unit test-integration coverage run migrate clean

PYTHON := python
PYTEST := pytest

help:
	@echo "LetAgentPay Backend — Makefile commands"
	@echo ""
	@echo "Setup:"
	@echo "  install          Install production dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  format           Format code with black and ruff --fix"
	@echo "  lint             Run linters (ruff, mypy)"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  coverage         Run tests with coverage report"
	@echo ""
	@echo "Running:"
	@echo "  run              Start the server (uvicorn --reload)"
	@echo "  migrate          Run alembic migrations"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean            Remove cache and build artifacts"
	@echo ""
	@echo "Note: release commands moved to root Makefile"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.test.txt

format:
	black .
	ruff check --fix .

lint:
	ruff check .
	mypy .

test:
	$(PYTEST) tests -v

test-unit:
	$(PYTEST) tests/unit -v

test-integration:
	$(PYTEST) tests/integration -v

coverage:
	$(PYTEST) --cov=app --cov-report=html --cov-report=term

run:
	uvicorn app.main:app --reload

migrate:
	alembic upgrade head

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
