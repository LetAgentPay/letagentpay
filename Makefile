.PHONY: help install install-dev format lint test test-unit test-integration coverage \
       run run-back run-front build migrate clean \
       release sdk-release publish-packages patch minor major \
       back-% front-%

PYTHON := python
PYTEST := pytest

BACKEND := backend
FRONTEND := frontend

RELEASE_TYPE := $(filter patch minor major,$(MAKECMDGOALS))

# -----------------------------------------------------------------------
# Help
# -----------------------------------------------------------------------

help:
	@echo "LetAgentPay — monorepo commands"
	@echo ""
	@echo "Setup:"
	@echo "  install          Install all dependencies (backend + frontend)"
	@echo "  install-dev      Install all dev dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  format           Format backend code (black + ruff --fix)"
	@echo "  lint             Lint backend (ruff + mypy) and frontend (next lint)"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run ALL tests (backend + frontend)"
	@echo "  test-unit        Run unit tests (backend + frontend)"
	@echo "  test-integration Run integration tests (backend only)"
	@echo "  coverage         Run tests with coverage (backend + frontend)"
	@echo ""
	@echo "Running:"
	@echo "  run              Start both backend and frontend (parallel)"
	@echo "  run-back         Start backend only (uvicorn --reload)"
	@echo "  run-front        Start frontend only (next dev)"
	@echo "  build            Build frontend for production"
	@echo "  migrate          Run alembic migrations"
	@echo ""
	@echo "Scoped commands:"
	@echo "  back-<cmd>       Run make <cmd> in backend/  (e.g. make back-test)"
	@echo "  front-<cmd>      Run npm run <cmd> in frontend/ (e.g. make front-dev)"
	@echo ""
	@echo "Release:"
	@echo "  release          Create release: make release patch|minor|major"
	@echo "  publish-packages Publish packages: make publish-packages [package] patch|minor|major"
	@echo "  sdk-release      (alias) Publish Python SDK: make sdk-release patch|minor|major"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean            Remove caches and build artifacts"

# -----------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------

install:
	cd $(BACKEND) && pip install -r requirements.txt
	cd $(FRONTEND) && npm install

install-dev:
	cd $(BACKEND) && pip install -r requirements.test.txt
	cd $(FRONTEND) && npm install

# -----------------------------------------------------------------------
# Code Quality
# -----------------------------------------------------------------------

format:
	cd $(BACKEND) && black . && ruff check --fix .

lint:
	cd $(BACKEND) && ruff check . && mypy .
	cd $(FRONTEND) && npm run lint

# -----------------------------------------------------------------------
# Testing
# -----------------------------------------------------------------------

test:
	cd $(BACKEND) && $(PYTEST) tests -v
	cd $(FRONTEND) && npm test

test-unit:
	cd $(BACKEND) && $(PYTEST) tests/unit -v
	cd $(FRONTEND) && npm test

test-integration:
	cd $(BACKEND) && $(PYTEST) tests/integration -v

coverage:
	cd $(BACKEND) && $(PYTEST) --cov=app --cov-report=html --cov-report=term
	cd $(FRONTEND) && npm run test:coverage

# -----------------------------------------------------------------------
# Running
# -----------------------------------------------------------------------

run:
	@echo "Starting backend (port 8000) and frontend (port 3000)..."
	@BACKEND=$(BACKEND) FRONTEND=$(FRONTEND) bash scripts/run_dev.sh

run-back:
	cd $(BACKEND) && uvicorn app.main:app --reload

run-front:
	cd $(FRONTEND) && npm run dev

build:
	cd $(FRONTEND) && npm run build

migrate:
	cd $(BACKEND) && alembic upgrade head

# -----------------------------------------------------------------------
# Scoped pass-through
# -----------------------------------------------------------------------

back-%:
	cd $(BACKEND) && $(MAKE) $*

front-%:
	cd $(FRONTEND) && npm run $*

# -----------------------------------------------------------------------
# Clean
# -----------------------------------------------------------------------

clean:
	cd $(BACKEND) && rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	cd $(BACKEND) && find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	cd $(BACKEND) && find . -type f -name "*.pyc" -delete 2>/dev/null || true
	cd $(FRONTEND) && rm -rf .next node_modules/.cache

# -----------------------------------------------------------------------
# Sync to GitHub repos
# -----------------------------------------------------------------------

sync:
	@bash scripts/sync_repos.sh both
	@bash scripts/sync_package.sh sdk
	@bash scripts/sync_package.sh sdk-js
	@bash scripts/sync_package.sh sdk-ai
	@bash scripts/sync_package.sh mcp-server
	@bash scripts/sync_package.sh openclaw-skill

sync-public:
	@bash scripts/sync_repos.sh public

sync-enterprise:
	@bash scripts/sync_repos.sh enterprise

sync-sdk:
	@bash scripts/sync_package.sh sdk

# -----------------------------------------------------------------------
# Content publish (no version bump — blog posts, docs, etc.)
# -----------------------------------------------------------------------

publish:
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Error: working tree is not clean."; \
		echo "Commit your content changes with a message starting with 'publish:', e.g.:"; \
		echo "  git commit -m 'publish: new blog post'"; \
		exit 1; \
	fi
	@MSG=$$(git log -1 --format=%s); \
	if ! echo "$$MSG" | grep -q '^publish:'; then \
		echo "Error: last commit message must start with 'publish:'"; \
		echo "Current: $$MSG"; \
		echo ""; \
		echo "Usage: commit content with 'publish: ...' message, then run make publish"; \
		exit 1; \
	fi; \
	echo "Publishing: $$MSG"; \
	git push; \
	echo ""; \
	echo "Syncing to enterprise repo..."; \
	bash scripts/sync_repos.sh enterprise; \
	echo ""; \
	echo "Content published. CI will rebuild and deploy frontend."

# -----------------------------------------------------------------------
# Release (unified versioning)
# -----------------------------------------------------------------------

release:
	@if [ -z "$(RELEASE_TYPE)" ]; then \
		echo "Usage: make release patch|minor|major"; \
		echo ""; \
		echo "  patch  - bug fixes, minor improvements (x.x.+1)"; \
		echo "  minor  - new features, backward compatible (x.+1.0)"; \
		echo "  major  - breaking changes (+1.0.0)"; \
		exit 1; \
	fi
	@if [ $$(echo "$(RELEASE_TYPE)" | wc -w | tr -d ' ') -ne 1 ]; then \
		echo "Error: specify exactly one of: patch, minor, major"; \
		exit 1; \
	fi
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Error: working tree is not clean. Commit all changes before release."; \
		exit 1; \
	fi
	@CURRENT=$$($(PYTHON) -c "from version import __version__; print(__version__)"); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	MINOR=$$(echo $$CURRENT | cut -d. -f2); \
	PATCH=$$(echo $$CURRENT | cut -d. -f3); \
	if [ "$(RELEASE_TYPE)" = "major" ]; then \
		MAJOR=$$((MAJOR + 1)); MINOR=0; PATCH=0; \
	elif [ "$(RELEASE_TYPE)" = "minor" ]; then \
		MINOR=$$((MINOR + 1)); PATCH=0; \
	else \
		PATCH=$$((PATCH + 1)); \
	fi; \
	NEW_VERSION="$$MAJOR.$$MINOR.$$PATCH"; \
	LAST_COMMIT=$$(git rev-parse --short HEAD); \
	echo "Current version: v$$CURRENT"; \
	echo "New version:     v$$NEW_VERSION"; \
	echo "Last commit:     $$LAST_COMMIT"; \
	echo ""; \
	if [ "$(RELEASE_TYPE)" = "major" ]; then \
		printf "Major version bump (breaking changes)! Continue? [y/N] "; \
		read CONFIRM; \
		if [ "$$CONFIRM" != "y" ] && [ "$$CONFIRM" != "Y" ]; then \
			echo "Aborted."; exit 1; \
		fi; \
	fi; \
	sed -i '' 's/__version__ = "[^"]*"/__version__ = "'$$NEW_VERSION'"/' version.py; \
	sed -i '' 's/__last_commit__ = "[^"]*"/__last_commit__ = "'$$LAST_COMMIT'"/' version.py; \
	git add version.py; \
	git commit -m "release: v$$NEW_VERSION"; \
	git push; \
	echo ""; \
	echo "Syncing to GitHub repos..."; \
	bash scripts/sync_repos.sh both; \
	bash scripts/sync_package.sh sdk; \
	bash scripts/sync_package.sh sdk-js; \
	bash scripts/sync_package.sh sdk-ai; \
	bash scripts/sync_package.sh mcp-server; \
	bash scripts/sync_package.sh openclaw-skill; \
	echo ""; \
	echo "Released v$$NEW_VERSION (CI: test → release → deploy)"

# -----------------------------------------------------------------------
# Package publishing (independent versioning)
# -----------------------------------------------------------------------

publish-packages:
	@if [ -z "$(RELEASE_TYPE)" ]; then \
		bash scripts/publish_packages.sh $(filter-out publish-packages,$(MAKECMDGOALS)); \
	else \
		bash scripts/publish_packages.sh $(filter-out publish-packages patch minor major,$(MAKECMDGOALS)) $(RELEASE_TYPE); \
	fi

sdk-release:
	@bash scripts/publish_packages.sh sdk $(RELEASE_TYPE)

patch minor major:
	@:
