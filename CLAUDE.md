# CLAUDE.md

## Projet

FlatBot — web app multi-utilisateurs de recherche d'appartements à Montréal (Kijiji + Centris + Rentals.ca → PostgreSQL + Telegram).

## Commandes

- `uv run pytest` — lancer les tests
- `uv run ruff check .` — linter
- `uv run ruff format .` — formatter
- `uv run python -m flat_research --serve` — lancer l'API backend (port 8080)
- `uv run python -m flat_research --scrape-multi` — lancer un cycle de scraping multi-user
- `uv run python -m flat_research --check` — health check des scrapers
- `cd frontend && npm run dev` — lancer le frontend React (port 5173)
- `docker compose up -d db` — lancer PostgreSQL local
- `DATABASE_URL=... uv run alembic upgrade head` — appliquer les migrations

## Conventions

- Python 3.12+, géré avec uv
- Frontend React + TypeScript + Vite
- Ruff pour lint et format (config dans pyproject.toml)
- Pre-commit hooks actifs (ruff lint + format)
- Ne jamais mettre de co-author dans les commits

## Vérifications systématiques

Avant chaque commit ou push :
- Lancer les tests (`uv run pytest`) et vérifier qu'ils passent tous
- Lancer le linter (`uv run ruff check .`)
- Vérifier le build frontend (`cd frontend && npm run build`)
- Vérifier qu'aucun secret, token ou clé API n'est présent en clair dans les fichiers modifiés
- Vérifier qu'il n'y a pas de code mort ajouté (fonctions non appelées, imports inutilisés)

Après chaque modification de code :
- Vérifier que la CI/CD fonctionne (le Dockerfile et le lockfile doivent rester synchronisés avec pyproject.toml)
- Si des dépendances changent, regénérer le lockfile (`uv lock`)

## Principes

- Simplicité maximale : pas de code mort, pas de fichiers inutiles, pas de champs non utilisés
- Ne pas faire de recherches web pour trouver du code d'autres personnes — uniquement les sites scrapés (kijiji.ca, centris.ca, rentals.ca)
- Les tests avec fixtures HTML/JSON servent de tests de régression si les sites changent leur structure
- Les secrets sont dans les variables d'environnement — jamais en clair dans le code ou les docs

## Architecture

- Backend : FastAPI (API REST JSON) + SQLAlchemy + PostgreSQL
- Frontend : React + Vite + TypeScript (SPA)
- Auth : JWT (access + refresh tokens) + bcrypt
- Scraping : scrapers découplés → matches_criteria() centralisé → notification per-user
- Deploy : Cloud Run Service (web) + Cloud Run Job (scraper) + Cloud SQL (PostgreSQL)
