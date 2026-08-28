# Changelog

## [Unreleased]

## [1.6.1] - 2026-08-28

### Fixed
- **500 on a NUL byte in the URL** — `\x00` in a path or query parameter reached asyncpg and crashed with `CharacterNotInRepertoireError` (Postgres cannot store `0x00` in `text`). This affected every route passing a raw string into a `WHERE` clause. A new `RejectNullBytesMiddleware` now returns 400 before the request reaches any handler
- **500 on an invalid email in `POST /api/v1/auth/send-link`** — the field was a bare `str`, so any string passed validation and reached Resend, which rejected it with its own `ValidationError`. The junk row had already been committed to `verification_tokens` by then. Added an `Email` type that strips, lowercases, and checks the format

### Improved
- **Cooldown on unhandled-exception alerts** — 5 minutes per (exception type, method, route template). A single vulnerability scanner previously produced dozens of identical notifications; keying on the route template rather than the raw path collapses fuzzed path parameters into one alert

## [1.6.0] - 2026-05-18

### Added
- **Velocity limit (ASPS 1.1)** — two new optional policy fields `requests_per_minute` and `requests_per_hour` cap the frequency of purchase requests independently of amount. Defends against runaway-loop scenarios where an agent spends many small amounts in rapid succession (the $437 and $607 incidents covered in the 2026-05-12 blog post). Velocity is the 2nd check in the policy engine (right after status), tracked via a Redis fixed-window counter. When the limit trips inside a window the audit log keeps exactly one rejected record — subsequent rejections in the same window reuse that `request_id` without writing a new row, protecting the audit log from runaway-loop spam. Available via JSON policy, the AI policy chat, and the dashboard policy preview. ASPS specification bumped to 1.1 (new standard `velocity_limit` check, Sections 9 and 9.1; fully backward-compatible with 1.0).

## [1.5.5] - 2026-05-12

### Fixed
- **Magic link verification race condition** — replaced `select + delete` with an atomic `DELETE ... RETURNING` so only one concurrent verify request with the same token can authenticate

### Improved
- **Security: bumped dependencies with known CVEs**
  - backend: `mako` 1.3.10 → 1.3.12 (CVE-2026-44307), `python-multipart` 0.0.26 → 0.0.28 (CVE-2026-42561), `urllib3` 2.6.3 → 2.7.0 (CVE-2026-44431, CVE-2026-44432)
  - frontend: `next` 16.2.3 → 16.2.6 (cache poisoning + middleware bypass advisories), plus `fast-uri`, `hono`, and `ip-address` via `shadcn` CLI update

## [1.5.4] - 2026-05-05

## [1.5.3] - 2026-05-04

## [1.5.2] - 2026-04-23

## [1.5.1] - 2026-04-23

## [1.5.0] - 2026-04-22

### Added
- **Custom categories** — categories are now per-account instead of 16 hardcoded global ones
  - CRUD API: `GET/POST/PUT/DELETE /api/v1/me/categories` + alias management
  - Import 16 default categories with 137 aliases in one click
  - AI-powered alias generation for custom categories
  - Unknown categories resolve to "other" and are flagged for owner review
  - Dashboard UI: Categories section in Settings
  - `GET /agent-api/categories` now returns per-account categories (requires auth)
  - AI Policy Assistant uses account's custom categories
  - Policy validation against account's category set
- **Agent token hashing** — tokens stored as SHA-256 hashes, lookup by hash
  - Token shown only on creation and regeneration
  - `POST /agents/{id}/regenerate-token` — token rotation endpoint
  - Token masking in API responses (`agt_••••••••••••`)
  - Dashboard: token shown at creation, then regenerate-only
- **Reconciliation service** — periodic Redis ↔ PostgreSQL counter sync (hourly)
- **x402 budget correction** — adjust budget when actual_amount differs from authorized_amount
  - tx_hash uniqueness (one tx cannot close two authorizations)

### Improved
- **Security hardening:**
  - Content-Security-Policy and Strict-Transport-Security headers
  - XSS protection in approval/rejection HTML pages
  - SSE newline sanitization
  - Telegram webhook secret verification
  - Wallet address validation (EVM / Solana)
  - tx_hash format validation (EVM / Solana)
  - Input limits on all Decimal fields (max 9,999,999)
  - OTP verification rate-limit per email
  - Atomic Redis counter operations (Lua scripts, floor-clamped decrements)
- Fail-closed for invalid schedule format (previously allowed requests through)
- Crypto exchange rate cache TTL reduced from 60s to 15s

### Breaking changes
- `GET /agent-api/categories` now requires authentication (Bearer token)
- Invalid schedule format now denies requests (fail-closed) instead of allowing

## [1.4.0] - 2026-04-18

### Added
- **Vercel AI SDK** — `@letagentpay/ai` npm package with 5 tools for `generateText()`/`streamText()`: requestPurchase, checkBudget, listCategories, myRequests, confirmPurchase
- **Google ADK integration** — example with multi-agent setup (researcher + buyer + coordinator with separate budgets)
- **Stripe integration guide** — architecture guide "LAP before Stripe" with Python and TypeScript examples
- `list_categories` and `confirm_purchase` tools added to all existing integrations (OpenAI Agents, LangChain, CrewAI)
- Unified package publish system (`publish_packages.sh` + `sync_package.sh`) with independent versioning
- CI workflows (test + release) for all npm packages (sdk-js, sdk-ai, mcp-server)

### Improved
- Category descriptions in tools now reference `listCategories` instead of hardcoded lists — preparing for custom categories (ASPS sec 3.3)
- Self-Hosted section added to all integration docs

### Fixed
- npm audit: protobufjs (critical), dompurify, hono (frontend + mcp-server)
- sdk-vercel-ai: migrated ai@4→ai@6, `parameters`→`inputSchema`

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

## [1.1.0] - 2026-04-07

### Added
- OpenClaw integration — TypeScript SDK, MCP server update, skill, documentation
- ASPS (Agent Spending Policy Specification) v0.1 draft
- CI: bandit (Python SAST), pip-audit, npm audit, gitleaks — security scanning in CI pipeline

### Fixed
- Security: upgraded anthropic 0.86.0 → 0.91.0 (CVE-2026-34450, CVE-2026-34452)
- Security: fixed vite vulnerabilities (path traversal, fs.deny bypass, WebSocket file read)

## [1.0.35] - 2026-04-06

## [1.0.33] - 2026-04-06

## [1.0.32] - 2026-04-06

## [1.0.31] - 2026-04-06

## [1.0.26] - 2026-04-04

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

## [1.0.11] - 2026-04-02

## [1.0.10] - 2026-04-02

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
