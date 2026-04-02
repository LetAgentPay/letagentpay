# Changelog

## [Unreleased]

## [1.0.9] - 2026-04-02

### Fixed
- CI: resolved Node.js 20 deprecation warnings in all GitHub Actions workflows
- CI: resolved ESLint unused variable warning in playground page
- Deploy: backend version is now baked into Docker image at build time (ARG APP_VERSION)

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
