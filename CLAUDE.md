# CLAUDE.md

## Projet

FlatBot — scraper d'appartements à Montréal (Kijiji + Centris → Google Sheets + Telegram).

## Commandes

- `uv run pytest` — lancer les tests
- `uv run ruff check .` — linter
- `uv run ruff format .` — formatter
- `uv run python -m flat_research` — exécution unique
- `uv run python -m flat_research --check` — health check

## Conventions

- Python 3.12+, géré avec uv
- Ruff pour lint et format (config dans pyproject.toml)
- Pre-commit hooks actifs (ruff lint + format)
- Ne jamais mettre de co-author dans les commits

## Vérifications systématiques

Avant chaque commit ou push :
- Lancer les tests (`uv run pytest`) et vérifier qu'ils passent tous
- Lancer le linter (`uv run ruff check .`)
- Vérifier qu'aucun secret, token ou clé API n'est présent en clair dans les fichiers modifiés (grep pour patterns type `bot_token=`, tokens Telegram, clés Google, PAT GitHub)
- Vérifier qu'il n'y a pas de code mort ajouté (fonctions non appelées, imports inutilisés, champs non utilisés)

Après chaque modification de code :
- Vérifier que la CI/CD fonctionne (le Dockerfile et le lockfile doivent rester synchronisés avec pyproject.toml)
- Si des dépendances changent, regénérer le lockfile (`uv lock`)

## Principes

- Simplicité maximale : pas de code mort, pas de fichiers inutiles, pas de champs non utilisés
- Ne pas faire de recherches web pour trouver du code d'autres personnes — uniquement les sites scrapés (kijiji.ca, centris.ca)
- Les tests avec fixtures HTML servent de tests de régression si les sites changent leur HTML
- Les secrets sont dans .env et config.yaml via ${VAR} — jamais en clair dans le code ou les docs
