# Changelog

## [Unreleased]

## [1.0.33] - 2026-04-06

- Enterprise version improvements

## [1.0.32] - 2026-04-06

- Enterprise version improvements

## [1.0.31] - 2026-04-06

- Enterprise version improvements

## [1.0.26] - 2026-04-04

- Enterprise version improvements

## [1.0.25] - 2026-04-04

### Fixed
- Monitoring: health alert cooldown used default 0, causing alerts to be skipped on fresh CI runners where time.monotonic() < 300s

## [1.0.16] - 2026-04-03

### Added
- Monitoring: Telegram alerts — auth failures, health check failures (Postgres/Redis) with 5-min cooldown, unhandled exceptions

### Fixed
- Auth: proxy password login through Route Handler to forward Set-Cookie in self-hosted mode
- Docs: added SITE_URL note for VPS deployment

### Improved
- Config: cleaned up .env.example — removed SaaS-only keys; .env.saas.example is now self-sufficient

## [1.0.15] - 2026-04-03

### Fixed
- Auth: revert debug error messages to user-friendly text

## [1.0.14] - 2026-04-03

### Fixed
- Auth: show actual error message on auth connection failure for debugging

## [1.0.13] - 2026-04-03

### Fixed
- Auth: prevent double OTP submission on mobile — race condition caused "Invalid or expired code" error despite successful registration

## [1.0.12] - 2026-04-02

- Enterprise version improvements

## [1.0.11] - 2026-04-02

- Enterprise version improvements

## [1.0.10] - 2026-04-02

- Enterprise version improvements

## [1.0.9] - 2026-04-02

### Fixed
- CI: resolved Node.js 20 deprecation warnings in all GitHub Actions workflows
- CI: resolved ESLint unused variable warning in playground page

## [1.0.2] - 2026-04-02

### Added
- Version field in `/api/v1/config/public` response
- Clickable version links on all pages — link to GitHub Release
- GitHub Releases with changelog notes created automatically on each release

## [1.0.1] - 2026-04-02

- Enterprise version improvements

## [1.0.0] - 2026-04-02

Initial public release.

### Core Features
- **Policy engine** — 8-check validation: agent status, category, per-request limit, schedule, daily/weekly/monthly limits, budget
- **Auto-approve** — trusted categories and small amounts approved automatically
- **Fund holding** — pending requests reserve budget, preventing overspend
- **Natural language policies** — describe rules in plain English, AI converts to structured config
- **Real-time dashboard** — approve/reject pending requests, SSE live updates
- **Budget rules** — account-level daily/weekly/monthly/total spending limits
- **Multi-channel notifications** — email, web push, Telegram
- **Agent API** — Bearer token auth, idempotency keys, category resolution
- **Self-hosted** — single `docker compose up -d`, password auth, no external dependencies required

### Integrations
- Python SDK (`pip install letagentpay`)
- MCP server (`npx letagentpay-mcp`)
- Framework examples: LangChain, OpenAI Agents SDK, CrewAI
