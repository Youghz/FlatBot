# FlatBot

Automated Montreal apartment finder. Scrapes rental listings from Kijiji, Centris and Rentals.ca, filters by criteria (price, bedrooms, neighbourhood, furnished, parking), stores results in a Google Sheet, and sends Telegram notifications for new matches.

## How it works

1. Scrapes Kijiji (JSON-LD), Centris (HTML) and Rentals.ca (GraphQL API) in parallel
2. Filters listings by price, bedrooms, neighbourhood, furnished/parking
3. Deduplicates against existing entries in Google Sheets
4. Sends a Telegram message for each new listing
5. Removes expired listings (past move-in dates) from the sheet

## Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Google Cloud credentials (ADC) for Sheets access
- Telegram bot token and chat ID

### Install

```bash
uv sync
```

### Configure

Copy `.env.example` to `.env` (or set environment variables directly):

```
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

Edit `config.yaml` to adjust search criteria (neighbourhoods, price range, bedrooms).

### Run

```bash
# Single run
uv run python -m flat_research

# Scheduled (every hour by default)
uv run python -m flat_research --schedule

# Health check (tests all connections)
uv run python -m flat_research --check
```

## Project structure

```
flat_research/
  __main__.py      # Entry point, config loading, orchestration
  models.py        # Listing dataclass
  parsing.py       # Shared parsing (Quebec notation, dates, furnished/parking)
  http_client.py   # HTTP session with retries and rate limiting
  sheets.py        # Google Sheets integration
  notifier.py      # Telegram notifications
  scrapers/
    centris.py     # Centris scraper (HTML)
    kijiji.py      # Kijiji scraper (JSON-LD)
    rentals.py     # Rentals.ca scraper (GraphQL API)
```

## Tests

```bash
uv run pytest
```

Tests use saved HTML/JSON fixtures to validate scrapers without network requests.

## Deployment

Runs as a Google Cloud Run Job, triggered hourly by Cloud Scheduler. See `.github/workflows/ci.yml` for the CI/CD pipeline.
