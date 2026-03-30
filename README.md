# FlatBot

Automated apartment search platform for Montreal. Scrapes rental listings from multiple sources, applies smart filtering based on user criteria, and sends real-time Telegram notifications.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Kijiji    │     │   Centris    │     │  Rentals.ca  │
│  (HTML/LD)  │     │  (HTML/CSS)  │     │  (GraphQL)   │
└──────┬──────┘     └──────┬───────┘     └──────┬───────┘
       │                   │                    │
       └───────────┬───────┘────────────────────┘
                   ▼
         ┌─────────────────┐
         │  Scraper Engine  │   Python + BeautifulSoup + curl_cffi
         │  (Cloud Run Job) │   Cloudflare bypass via TLS fingerprinting
         └────────┬────────┘
                  ▼
         ┌─────────────────┐
         │   PostgreSQL    │   Cloud SQL
         │   (listings)    │   Alembic migrations
         └────────┬────────┘
                  ▼
    ┌─────────────┴──────────────┐
    ▼                            ▼
┌──────────┐            ┌──────────────┐
│ Telegram │            │   React SPA  │
│   Bot    │            │  (Dashboard) │
│  Notifs  │            │              │
└──────────┘            └──────────────┘
```

## Tech Stack

### Backend
- **Python 3.12** with **FastAPI** — REST API with JWT authentication
- **SQLAlchemy 2.0** + **PostgreSQL** — ORM with Alembic migrations
- **BeautifulSoup4** — HTML parsing for Kijiji and Centris
- **curl_cffi** — Chrome TLS fingerprint impersonation to bypass Cloudflare
- **bcrypt** — Password hashing with timing-safe verification
- **python-jose** — JWT access/refresh token management
- **slowapi** — Rate limiting on authentication and webhook endpoints

### Frontend
- **React 19** + **TypeScript 5.9** — Single Page Application
- **Vite 8** — Build tooling with HMR
- **React Router 7** — Client-side routing with protected routes
- **CSS Custom Properties** — Dark theme design system, no framework dependency

### Infrastructure
- **Google Cloud Run** — Serverless deployment (web service + scraper job)
- **Google Cloud SQL** — Managed PostgreSQL
- **Google Cloud Storage** — Test fixture persistence for regression testing
- **Docker** — Multi-stage builds with non-root user, BuildX layer caching
- **GitHub Actions** — CI/CD with lint, test, build, deploy, smoke test pipeline

### Data Pipeline
- **NLP-based field extraction** — Furnished/parking/move-in detection from French+English text
- **Tri-state classification** — `True`/`False`/`"semi"` for appliances-only listings
- **Fixture-based regression testing** — 18+ hand-labeled HTML fixtures with automated accuracy tracking
- **User feedback loop** — Dashboard corrections auto-generate test fixtures via GCS bucket

## Key Features

- **Multi-source scraping** — Kijiji (JSON-LD), Centris (HTML), Rentals.ca (GraphQL)
- **Per-user criteria** — Price, bedrooms, neighbourhoods, furnished, parking, move-in date
- **Smart notifications** — Telegram bot with structured message format
- **Inline editing** — Correct extracted fields directly in the dashboard
- **Automated testing** — User corrections become regression tests automatically
- **Extraction accuracy tracking** — `scripts/eval.py` reports accuracy per field

## Development

```bash
# Install dependencies
uv sync

# Run API server
uv run python -m flat_research --serve

# Run scraper
uv run python -m flat_research --scrape-multi

# Run tests (206 tests)
uv run pytest

# Extraction accuracy report
uv run python scripts/eval.py -v

# Frontend
cd frontend && npm ci && npm run dev
```
