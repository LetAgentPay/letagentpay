# Contributing to LetAgentPay

Thank you for your interest in contributing! This guide will help you get started.

## Getting Started

### Prerequisites

- Python 3.14+
- Node.js 22+
- Docker & Docker Compose (for PostgreSQL and Redis)
- Make

### Setup

```bash
# Clone the repository
git clone https://github.com/letagentpay/letagentpay
cd letagentpay

# Start infrastructure
docker compose up -d  # PostgreSQL + Redis

# Install all dependencies
make install-dev

# Run migrations
make migrate

# Run the app (backend :8000 + frontend :3000)
make run
```

### Running Tests

```bash
make test-unit    # All unit tests (backend + frontend)
make lint         # Linters (ruff, mypy, eslint)
make format       # Auto-format code
```

## Making Changes

### Branch Naming

- `feat/description` — new features
- `fix/description` — bug fixes
- `docs/description` — documentation
- `refactor/description` — code refactoring

### Code Style

**Backend (Python):**
- Formatter: black (line-length 88)
- Linter: ruff
- Type checking: mypy
- Run `make format && make lint` before committing

**Frontend (TypeScript):**
- Linter: ESLint (next lint)
- Run `npm run lint` in `frontend/`

### Writing Tests

**Backend:** pytest-asyncio, test files in `backend/tests/unit/` named `test_*.py`

**Frontend:** Vitest + React Testing Library, test files in `frontend/src/__tests__/` named `*.test.tsx`

Every new feature should include tests.

## Pull Requests

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes with tests
4. Run `make format && make lint && make test-unit`
5. Submit a PR against `main`

### PR Guidelines

- Keep PRs focused — one feature or fix per PR
- Write a clear description of what and why
- Reference related issues if applicable
- Ensure CI passes

## Architecture

See [docs/architecture.md](docs/architecture.md) for a system overview.

### Key Principles

- **Core is self-contained** — everything in `backend/app/` and `frontend/src/` works without enterprise modules
- **Enterprise is optional** — `backend/ee/` is loaded dynamically, core never imports from it
- **Policy engine is the heart** — `backend/app/services/policy_engine.py` runs 8 validation checks on every purchase request

### What Goes Where

| Change | Location |
|--------|----------|
| New policy check | `backend/app/services/policy_engine.py` |
| New Agent API endpoint | `backend/app/routers/agent_api.py` |
| New dashboard page | `frontend/src/app/dashboard/` |
| New React component | `frontend/src/components/` |
| API client method | `frontend/src/lib/api.ts` |
| Database model change | `backend/app/models.py` + new Alembic migration |

## CLA

We require a Contributor License Agreement (CLA) for all contributions. The CLA bot will automatically comment on your first PR with instructions.

## Code of Conduct

Be respectful and constructive. We're building something useful together.

## Questions?

Open an [issue](https://github.com/letagentpay/letagentpay/issues) — we're happy to help.
