#!/bin/bash
# =============================================================
# Flat Research - Setup Script
# =============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=== Flat Research Setup ==="

# 1. Install dependencies via uv
echo "Installing dependencies with uv..."
uv sync

# 2. Check config
if [ ! -f "config.yaml" ]; then
    echo "ERROR: config.yaml not found!"
    exit 1
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "NEXT STEPS:"
echo ""
echo "1. GOOGLE SHEETS - Application Default Credentials (no key file):"
echo "   a. Install gcloud CLI: https://cloud.google.com/sdk/docs/install"
echo "   b. gcloud auth login"
echo "   c. gcloud auth application-default login \\"
echo "        --impersonate-service-account=SA@PROJECT.iam.gserviceaccount.com"
echo "   d. Enable APIs in your project:"
echo "      gcloud services enable sheets.googleapis.com drive.googleapis.com"
echo ""
echo "2. TELEGRAM BOT:"
echo "   a. Open Telegram, search for @BotFather"
echo "   b. Send /newbot and follow instructions"
echo "   c. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env"
echo ""
echo "3. RUN:"
echo "   uv run python -m flat_research              # Run once"
echo "   uv run python -m flat_research --schedule   # Run every hour"
echo ""
echo "4. CRON (optional - run every hour automatically):"
echo "   crontab -e"
echo "   Add: 0 * * * * cd $PROJECT_DIR && uv run python -m flat_research >> flat-research.log 2>&1"
