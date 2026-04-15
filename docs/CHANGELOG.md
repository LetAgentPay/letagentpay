# Changelog

## [Unreleased]

## [1.3.0] - 2026-04-15

### Added
- **x402 integration** — policy middleware for crypto-micropayments (USDC on Base)
  - 5 API endpoints: authorize, report, budget, wallets, wallets/create
  - Policy checks: chain whitelist, domain filter, category, limits, budget, stablecoin depeg protection
  - Exchange rate service (Coinbase + CoinGecko, Redis cache)
  - Coinbase CDP wallet provider integration
  - Dashboard: settlement badge, tx_hash link to Basescan, x402 analytics
  - Python SDK: `client.x402.authorize()`, `report()`, `budget()`, wallets
  - TypeScript SDK: `client.x402.authorize()`, `report()`, `budget()`, wallets
  - MCP server: `x402_authorize`, `x402_report`, `x402_budget` tools
  - ASPS spec: x402 settlement policy extension (section 12.4)
  - Self-host guide: CDP configuration, authentication modes
  - DB migration: settlement fields, agent_wallets, exchange_rates tables
- Extension point `getEEPublicLinks()` in ee-hooks for enterprise navigation links

### Fixed
- Footer now shows the same links as the navigation bar (added Playground)
- Enterprise version improvements

## [1.2.3] - 2026-04-10

### Fixed
- Docker: prebuild script no longer overwrites pre-copied spec files with placeholders inside Docker container

## [1.2.2] - 2026-04-10

### Fixed
- Docker: CI now copies spec markdown files into frontend before Docker build (both public and enterprise workflows)

## [1.2.1] - 2026-04-10

### Fixed
- Docker: ASPS spec pages failed to build — markdown files were outside Docker context. Prebuild script now copies specs into public/asps/

## [1.2.0] - 2026-04-10

### Added
- ASPS v1 specification finalized (status: Stable) — formalized from existing policy engine implementation
- ASPS v2: Mission Policy specification (status: Draft) — multi-agent coordination with shared budgets, phases, dynamic allocation, constraints, escalation, competitive allocation, risk scoring
- ASPS v1 JSON Schema published at `/schemas/asps/v0.1/policy.json`
- Website: `/asps` landing page with v1/v2 overview and architecture diagram
- Website: `/asps/spec` renders v1 spec directly from markdown (single source of truth)
- Website: `/asps/v2` renders Mission Policy spec from markdown
- Website: `/asps/use-cases` — 5 visual use cases with diagrams (travel, incident response, marketing, procurement, customer service)
- Markdown renderer component (react-markdown + remark-gfm + rehype-slug)
- Policy editor extracted into reusable component with tests
- SEO: dynamic `sitemap.xml` with all public pages
- SEO: `robots.txt` with crawl rules (disallow dashboard, auth/verify, api)
- SEO: BreadcrumbList JSON-LD in root layout for SERP navigation
- SEO: Article JSON-LD on About page, TechArticle JSON-LD on ASPS v1 Specification page

### Fixed
- Timezone-aware datetime comparisons with asyncpg — `ensure_utc()` helper prevents TypeError on naive vs aware datetime in expiry checks
- SEO: Sign In page marked `noindex` — excluded from search indexing
- SEO: added metadata for 404 page (title + noindex)

## [1.1.1] - 2026-04-08

### Fixed
- Enterprise version improvements

## [1.1.0] - 2026-04-07

### Added
- OpenClaw integration — TypeScript SDK, MCP server update, skill, documentation
- ASPS (Agent Spending Policy Specification) v0.1 draft
- CI: bandit (Python SAST), pip-audit, npm audit, gitleaks — security scanning in CI pipeline

### Fixed
- Security: upgraded anthropic 0.86.0 → 0.91.0 (CVE-2026-34450, CVE-2026-34452)
- Security: fixed vite vulnerabilities (path traversal, fs.deny bypass, WebSocket file read)
- Enterprise version improvements

## [1.0.35] - 2026-04-06

- Enterprise version improvements

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
