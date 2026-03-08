# Flat Research -- Documentation technique

## 1. Vue d'ensemble

Flat Research est un outil automatise de veille immobiliere pour la region de Montreal. Il scrape periodiquement les annonces de location sur Kijiji et Centris, filtre les resultats selon des criteres configurables (prix, nombre de chambres, quartier, meuble, parking), enregistre les nouvelles annonces dans un Google Sheet et envoie des notifications Telegram en temps reel.

Le projet est concu pour fonctionner en tant que Cloud Run Job sur Google Cloud Platform, declenche toutes les heures par Cloud Scheduler.

---

## 2. Architecture

### Diagramme des composants

```
+-------------------+      +-------------------+
|   config.yaml     |      |      .env         |
|  (criteres, IDs)  |      | (secrets Telegram)|
+--------+----------+      +--------+----------+
         |                           |
         +----------+   +------------+
                    |   |
                    v   v
              +-----+---+------+
              |    main.py     |
              | (orchestrateur)|
              +-------+--------+
                      |
         +------------+------------+
         |  ThreadPoolExecutor     |
         |  (execution parallele)  |
         +---+----------------+----+
             |                |
             v                v
   +---------+------+  +-----+---------+
   | scrapers/      |  | scrapers/     |
   | kijiji.py      |  | centris.py    |
   +--------+-------+  +-------+-------+
            |                   |
            v                   v
   +--------+-------------------+-------+
   |          http_client.py            |
   |  (session, retry, rate limiting)   |
   +------------------------------------+
            |                   |
            v                   v
   +--------+-------+  +-------+--------+
   | www.kijiji.ca  |  | www.centris.ca |
   +----------------+  +----------------+

              +-------+--------+
              |    main.py     |
              +---+--------+---+
                  |        |
                  v        v
        +---------+--+  +--+-----------+
        | sheets.py  |  | notifier.py  |
        | (Google    |  | (Telegram)   |
        |  Sheets)   |  +--------------+
        +------------+
```

### Flux de donnees

```
1. Chargement config.yaml + resolution des variables .env
2. Scraping parallele (Kijiji + Centris)
   |-- Construction des URL avec filtres
   |-- Requete HTTP (session avec retry + rate limiting)
   |-- Parsing HTML (BeautifulSoup)
   |-- Filtrage par criteres (prix, chambres, quartier)
3. Deduplication par ID dans Google Sheets
4. Ajout des nouvelles annonces au Sheet
5. Notification Telegram pour les nouveaux resultats
```

---

## 3. Structure du projet

```
flat-research/
|-- main.py                  Orchestrateur principal, chargement config, execution parallele
|-- config.yaml              Criteres de recherche, sources, parametres Sheets/Telegram
|-- http_client.py           Client HTTP partage avec retry et rate limiting par domaine
|-- sheets.py                Integration Google Sheets (ADC, sanitization, deduplication)
|-- notifier.py              Notifications Telegram (formatage HTML, chunking)
|-- scrapers/
|   |-- __init__.py          Package scrapers (vide)
|   |-- kijiji.py            Scraper Kijiji + dataclass Listing + notation quebecoise
|   |-- centris.py           Scraper Centris + construction URL par arrondissement
|-- tests/
|   |-- __init__.py          Package tests (vide)
|   |-- fixtures/            Fichiers HTML sauvegardes pour tests hors-ligne
|   |-- test_parsing.py      Tests unitaires : chambres, prix, meuble/parking, criteres
|   |-- test_scrapers.py     Tests d'integration : parsing de fixtures HTML reelles
|   |-- test_sheets.py       Tests de sanitization anti-injection
|   |-- test_config.py       Tests de resolution des variables d'environnement
|-- deploy.sh                Script de deploiement GCP (Cloud Run Jobs + Scheduler)
|-- setup.sh                 Script d'installation locale (uv sync + instructions)
|-- Dockerfile               Image Docker (python:3.12-slim + uv)
|-- pyproject.toml           Dependances Python (uv/pip)
|-- uv.lock                  Fichier de verrouillage des dependances (uv)
|-- .env                     Variables d'environnement locales (secrets Telegram)
|-- .gitignore               Exclusions Git (.env, credentials, __pycache__)
|-- .dockerignore            Exclusions Docker (.venv, .env, .git)
```

---

## 4. Composants detailles

### 4.1 Scrapers

Les deux scrapers partagent la meme dataclass `Listing` (definie dans `scrapers/kijiji.py`) et suivent la meme interface : `scrape(config, session) -> list[Listing]`.

#### 4.1.1 Kijiji (`scrapers/kijiji.py`)

**Construction de l'URL :**

L'URL est construite a partir du chemin de categorie fixe (`/b-appartement-condo/ville-de-montreal/c37l1700281`) avec des parametres de requete dynamiques :

| Parametre           | Source config            | Exemple     |
|---------------------|--------------------------|-------------|
| `rb`                | `criteria.price_min`     | `2000`      |
| `re`                | `criteria.price_max`     | `3000`      |
| `numberbedrooms`    | `criteria.bedrooms_min`  | `3`         |
| `furnished`         | `criteria.furnished`     | `1`         |
| `numberparkingspots`| `criteria.parking`       | `1`         |

**Parsing HTML :**

Le parser utilise BeautifulSoup avec une strategie de selecteurs en cascade pour resister aux changements de structure HTML de Kijiji :

1. `[data-testid='listing-card']` (selecteur principal)
2. `div.search-item, li.regular-ad, div[data-listing-id]` (fallback)
3. `section ul li` (dernier recours)

Pour chaque carte, les elements suivants sont extraits : ID, titre, prix, URL, adresse, description, image.

**Notation quebecoise des chambres :**

La fonction `_extract_bedrooms_from_text()` gere la convention du Quebec ou le nombre de pieces inclut la cuisine et le salon :

| Notation        | Pieces totales | Chambres calculees |
|-----------------|----------------|--------------------|
| 3 1/2           | 3              | 1                  |
| 4 1/2           | 4              | 2                  |
| 5 1/2           | 5              | 3                  |
| 6 1/2           | 6              | 4                  |

Formule : `chambres = total_pieces - 2`

Les formats reconnus sont : `5 1/2`, `5 et demi`, `5.5`, et le caractere Unicode `5\u00bd`. Si une mention explicite est trouvee (par exemple "3 chambres"), elle a priorite sur la notation quebecoise.

**Detection meuble/parking avec negation :**

La fonction `_check_furnished_parking()` detecte d'abord les negations avant de chercher les termes positifs. Voir la section Securite pour les details.

**Filtrage par quartier :**

La fonction `_matches_criteria()` utilise un dictionnaire de variantes pour chaque quartier cible. Par exemple, "Mile-Ex" correspond aussi a "mile end" et "marconi-alexandra". La recherche est effectuee dans le texte combine (adresse + titre + quartier + description).

#### 4.1.2 Centris (`scrapers/centris.py`)

**Construction des URL :**

Centris utilise une convention de filtres dans le chemin de l'URL. La fonction `_build_urls()` convertit les quartiers en slugs d'arrondissement via le dictionnaire `BOROUGH_SLUGS` :

| Quartier        | Slug d'arrondissement                           |
|-----------------|--------------------------------------------------|
| Villeray        | `montreal-villeray-saint-michel-parc-extension`  |
| Mile-Ex         | `montreal-villeray-saint-michel-parc-extension`  |
| Petite-Italie   | `montreal-villeray-saint-michel-parc-extension`  |
| Petite-Patrie   | `montreal-rosemont-la-petite-patrie`             |
| Rosemont        | `montreal-rosemont-la-petite-patrie`             |
| Ahuntsic        | `montreal-ahuntsic-cartierville`                 |

Plusieurs quartiers peuvent correspondre au meme arrondissement. La deduplication est faite avec `dict.fromkeys()` pour conserver l'ordre tout en eliminant les doublons.

URL resultante : `https://www.centris.ca/fr/propriete~a-louer~{slug}`

**Parsing HTML :**

Les cartes sont selectionnees avec `div.property-thumbnail-item`. Les donnees structurees (prix, ID MLS) sont extraites depuis des balises `<meta itemprop="...">`. Le nombre de chambres provient de `div.cac` ; en fallback, la notation quebecoise est utilisee.

Un ensemble `seen_ids` evite les doublons entre les pages d'arrondissements differents.

### 4.2 Client HTTP (`http_client.py`)

**Reutilisation de session :**

Chaque scraper recoit sa propre instance `requests.Session` via `create_session()`. La session maintient un pool de connexions TCP, ce qui evite le cout de la negociation TLS pour chaque requete.

**Strategie de retry :**

| Parametre                      | Valeur                       |
|--------------------------------|------------------------------|
| Nombre total de tentatives     | 3                            |
| Facteur de backoff             | 1 (1s, 2s, 4s)              |
| Codes HTTP avec retry          | 429, 500, 502, 503, 504     |
| Respect de `Retry-After`       | Oui                          |

L'adaptateur `HTTPAdapter` est monte sur les schemas `https://` et `http://`.

**Rate limiting :**

La fonction `get()` impose un delai minimum de 1 seconde entre les requetes vers un meme domaine. Le suivi est effectue par un dictionnaire global `_last_request_time` indexe par `netloc`.

**Headers :**

Un User-Agent Chrome/macOS et un `Accept-Language: fr-CA` sont envoyes pour obtenir le contenu en francais.

### 4.3 Google Sheets (`sheets.py`)

**Authentification :**

L'authentification utilise Application Default Credentials (ADC) via `google.auth.default()`. Aucun fichier de cle JSON n'est embarque dans le code. En local, on utilise `gcloud auth application-default login`. Sur Cloud Run, le compte de service du job fournit les credentials automatiquement.

**Scopes requis :** `spreadsheets` et `drive`.

**Structure du Sheet :**

| Colonne     | Contenu                          |
|-------------|----------------------------------|
| A           | ID (kijiji_123 ou centris_MLS)   |
| B           | Source                           |
| C           | Titre                            |
| D           | Prix ($)                         |
| E           | Chambres                         |
| F           | Adresse                          |
| G           | Quartier                         |
| H           | Meuble (Oui/Non)                 |
| I           | Parking (Oui/Non)                |
| J           | URL                              |
| K           | Date ajout                       |
| L           | Description (200 caracteres max) |

**Sanitization anti-injection :**

La fonction `_sanitize_cell()` prefixe les cellules commencant par `=`, `+`, `-` ou `@` avec une apostrophe (`'`) pour empecher l'interpretation comme formule. Voir la section Securite.

**Deduplication :**

Avant chaque insertion, la colonne A (IDs) est lue en entier. Seules les annonces dont l'ID n'existe pas deja sont ajoutees. L'insertion se fait en batch avec `sheet.append_rows()`.

**Creation automatique :**

Si le `spreadsheet_id` est fourni dans la config, le sheet est ouvert directement. Sinon, il est recherche par nom ou cree automatiquement avec un partage public en lecture.

### 4.4 Notificateur Telegram (`notifier.py`)

**Formatage HTML :**

Les messages utilisent le mode `parse_mode=HTML` de l'API Telegram. Les titres et adresses sont echappes avec `html.escape()` pour eviter les injections de balisage. Chaque annonce est formatee avec :

- Titre en gras (`<b>`)
- Prix, chambres, adresse
- Statut meuble/parking
- Lien vers l'annonce (`<a href="...">`)
- Lien vers le Google Sheet en fin de message

**Chunking des messages :**

L'API Telegram impose une limite de 4096 caracteres par message. Le notificateur decoupe le message en segments de 4000 caracteres maximum (marge de securite) et envoie chaque segment individuellement.

**Gestion d'erreurs :**

Les erreurs de notification n'interrompent pas le cycle principal. Si le `bot_token` ou le `chat_id` ne sont pas configures, la notification est simplement ignoree avec un avertissement dans les logs.

### 4.5 Configuration (`config.yaml` + `.env`)

**Structure YAML :**

Le fichier `config.yaml` contient cinq sections :

| Section          | Contenu                                                |
|------------------|--------------------------------------------------------|
| `criteria`       | Ville, type, quartiers, chambres min, fourchette prix  |
| `sources`        | Liste des scrapers actifs (`kijiji`, `centris`)        |
| `google_sheets`  | Nom et ID du spreadsheet                               |
| `telegram`       | Token bot et chat ID (references `${...}`)             |
| `schedule`       | Intervalle en minutes                                  |

**Resolution des variables d'environnement :**

La fonction `_resolve_env_vars()` dans `main.py` parcourt recursivement la structure YAML et remplace les placeholders `${VAR}` par les valeurs correspondantes de `os.environ`. Les variables sont chargees depuis `.env` via `python-dotenv` au moment du `load_config()`. Si une variable n'existe pas, le placeholder est conserve tel quel.

### 4.6 Orchestrateur (`main.py`)

**Execution parallele :**

La fonction `run_once()` utilise `concurrent.futures.ThreadPoolExecutor` pour executer les scrapers en parallele. Chaque scraper recoit sa propre session HTTP. Le nombre de workers correspond au nombre de scrapers actifs (actuellement 2).

**Modes d'execution :**

| Mode                       | Commande                         | Comportement                       |
|----------------------------|----------------------------------|------------------------------------|
| Execution unique           | `python main.py`                 | Un seul cycle scrape-sheet-notify  |
| Mode planifie              | `python main.py --schedule`      | Boucle infinie avec sleep          |
| Health check               | `python main.py --check`         | Teste chaque composant et exit 0/1 |
| Cloud Run Job              | Dockerfile ENTRYPOINT            | Execution unique (par defaut)      |

**Codes de sortie :**

- `exit 0` : cycle termine avec succes (ou aucune annonce trouvee)
- `exit 1` : erreur critique (Google Sheets inaccessible, Telegram en echec, health check KO)

Cloud Run utilise le code de sortie pour marquer l'execution comme `Completed` ou `Failed`, ce qui permet le monitoring via Cloud Logging et les alertes.

**Mode `--check` (health check) :**

La fonction `run_check()` teste les 4 composants en sequence :

| Composant      | Test effectue                                                      |
|----------------|--------------------------------------------------------------------|
| Kijiji         | HTTP GET sur la page de recherche, verifie status 200              |
| Centris        | HTTP GET sur une page d'arrondissement, verifie status 200         |
| Google Sheets  | Authentification ADC + lecture de la premiere ligne du spreadsheet  |
| Telegram       | Envoi d'un message de test au chat configure                       |

Si un composant echoue, le detail est loge et le code de sortie est 1. Ce mode est utilise comme smoke test apres chaque deploiement.

**Pipeline par cycle :**

1. Scraping parallele de toutes les sources
2. Aggregation des resultats
3. Ajout au Google Sheet (deduplication interne)
4. Notification Telegram (uniquement pour les nouvelles annonces)

Chaque etape est isolee dans un bloc `try/except`. Une erreur dans une etape n'empeche pas les etapes suivantes de s'executer (sauf si le Sheet echoue, auquel cas la notification est sautee car il n'y a pas de `sheet_url` disponible).

---

## 5. Securite

### 5.1 Aucun secret dans le code

- **Google Sheets** : Authentification via Application Default Credentials (ADC). Aucun fichier `credentials.json` n'est versionne. En production, le compte de service Cloud Run fournit les credentials.
- **Telegram** : Les tokens sont stockes dans `.env` localement et dans Secret Manager sur GCP. Le fichier `config.yaml` contient uniquement des references `${TELEGRAM_BOT_TOKEN}` et `${TELEGRAM_CHAT_ID}`.
- **Secret Manager** : Le script `deploy.sh` cree les secrets dans GCP Secret Manager et les injecte dans le Cloud Run Job via `--set-secrets`.

### 5.2 Fichiers `.env` et `.gitignore`

Le fichier `.gitignore` exclut explicitement :

- `.env` (secrets Telegram)
- `credentials.json` et `*.json` (cles de service)
- `__pycache__/`, `.venv/`

Le fichier `.dockerignore` exclut egalement `.env`, `.git/` et les logs.

### 5.3 Protection contre l'injection de formules dans Sheets

La fonction `_sanitize_cell()` dans `sheets.py` protege contre les attaques par injection de formules (CSV injection). Toute cellule commencant par l'un des caracteres suivants est prefixee par une apostrophe :

| Caractere | Risque                                       |
|-----------|----------------------------------------------|
| `=`       | Execution de formule arbitraire              |
| `+`       | Interpretation comme formule                 |
| `-`       | Interpretation comme formule                 |
| `@`       | Appel de fonction externe                    |

Exemple : une annonce avec le titre `=SUM(A1:A10)` sera stockee comme `'=SUM(A1:A10)`.

### 5.4 Detection de negation (meuble, parking)

La fonction `_check_furnished_parking()` dans `scrapers/kijiji.py` verifie les negations **avant** les termes positifs pour eviter les faux positifs :

**Negations meuble :**

- "non meuble", "non-meuble", "pas meuble", "unfurnished"

**Negations parking :**

- "pas de parking", "pas de stationnement", "no parking", "sans parking"

Ainsi, une annonce contenant "non meuble" ne sera pas marquee comme meublee, meme si le mot "meuble" est present dans le texte.

---

## 6. Tests

### Ce qui est teste

| Fichier              | Portee                                                         |
|----------------------|----------------------------------------------------------------|
| `test_parsing.py`    | Extraction des chambres (notation QC + standard), parsing du prix, detection meuble/parking avec negation, correspondance des criteres (prix, chambres, quartier, variantes) |
| `test_scrapers.py`   | Parsing de fixtures HTML reelles de Kijiji et Centris, verification des champs obligatoires, construction et deduplication des URL Centris |
| `test_sheets.py`     | Sanitization anti-injection pour tous les caracteres dangereux, passthrough des valeurs non-string |
| `test_config.py`     | Resolution `${VAR}` dans les strings, dicts et listes ; passthrough des non-strings ; conservation des variables inconnues |

### Strategie de fixtures

Les tests de scrapers (`test_scrapers.py`) utilisent des fichiers HTML sauvegardes dans `tests/fixtures/` (`centris_search.html`, `kijiji_search.html`). Ces fixtures permettent :

- De tester le parsing sans effectuer de requetes reseau
- De servir de tests de regression si la structure HTML des sites change
- D'isoler les tests de la disponibilite des sites externes

Les tests unitaires (`test_parsing.py`) utilisent des donnees parametrisees directement dans le code de test via `@pytest.mark.parametrize`.

### Execution des tests

```bash
# Tous les tests
uv run pytest

# Un fichier specifique
uv run pytest tests/test_parsing.py

# Mode verbose
uv run pytest -v
```

---

## 7. Deploiement GCP

### Architecture Cloud

```
+-------------------+         +---------------------+
| Cloud Scheduler   |  HTTP   | Cloud Run Jobs      |
| (cron: 17 * * * *)+-------->+ (flat-research)     |
+-------------------+  POST   | - python:3.12-slim  |
                              | - 512 Mi RAM        |
                              | - timeout 300s      |
                              +---+--------+--------+
                                  |        |
                   +--------------+        +----------+
                   v                                  v
          +--------+---------+            +-----------+--------+
          | Secret Manager   |            | Google Sheets API  |
          | - telegram-bot-  |            | (via ADC du        |
          |   token          |            |  service account)  |
          | - telegram-chat- |            +--------------------+
          |   id             |
          +------------------+

          +------------------+
          | Artifact Registry|
          | (image Docker)   |
          +------------------+

          +------------------+
          | Cloud Build      |
          | (build & push)   |
          +------------------+
```

### Composants GCP utilises

| Service              | Role                                              | Region                     |
|----------------------|---------------------------------------------------|----------------------------|
| Cloud Run Jobs       | Execution du scraper (sans serveur)               | `northamerica-northeast1`  |
| Cloud Scheduler      | Declenchement horaire (cron `17 * * * *`)         | `northamerica-northeast1`  |
| Secret Manager       | Stockage des tokens Telegram                      | Global                     |
| Artifact Registry    | Stockage de l'image Docker                        | `northamerica-northeast1`  |
| Cloud Build          | Build de l'image Docker depuis le code source     | `northamerica-northeast1`  |

### Script de deploiement (`deploy.sh`)

Le script execute les etapes suivantes dans l'ordre :

1. **Activation des API** requises (Run, Artifact Registry, Scheduler, Secret Manager, Sheets, Drive)
2. **Attribution des roles IAM** au compte de service (`run.invoker`, `cloudscheduler.admin`)
3. **Activation des API Sheets/Drive** — necessaires pour que le SA puisse acceder au Google Sheet depuis Cloud Run
4. **Creation du depot Artifact Registry** pour stocker l'image Docker
5. **Build et push** de l'image Docker via Cloud Build
6. **Creation/mise a jour des secrets** dans Secret Manager (Telegram bot token + chat ID)
7. **Attribution de l'acces aux secrets** pour le compte de service (`secretmanager.secretAccessor`)
8. **Creation/mise a jour du Cloud Run Job** avec injection des secrets en variables d'environnement
9. **Creation/mise a jour du Cloud Scheduler** (cron `17 * * * *` = minute 17 de chaque heure)
10. **Smoke test** : execution du job avec `--check` et verification du statut

Le script est idempotent : chaque commande `create` a un fallback `update` en cas d'existence prealable.

### Smoke test post-deploiement

L'etape 10 du script de deploiement execute automatiquement un health check apres le deploiement :

```bash
gcloud run jobs execute flat-research --args="--check" --wait
```

Le flag `--wait` bloque jusqu'a la fin de l'execution. Le script verifie ensuite le statut de la derniere execution via `gcloud run jobs executions list`. Si le statut n'est pas `Completed`, un avertissement est affiche avec la commande pour consulter les logs.

Ce smoke test valide que le container demarre correctement, que les secrets sont injectes, que les API Sheets/Drive sont accessibles, et que Telegram repond.

### APIs GCP requises

| API                              | Raison                                                          |
|----------------------------------|------------------------------------------------------------------|
| `run.googleapis.com`             | Cloud Run Jobs                                                  |
| `artifactregistry.googleapis.com`| Stockage de l'image Docker                                      |
| `cloudscheduler.googleapis.com`  | Declenchement horaire                                           |
| `secretmanager.googleapis.com`   | Stockage des secrets Telegram                                   |
| `sheets.googleapis.com`          | Acces au Google Sheet depuis le SA                              |
| `drive.googleapis.com`           | Ouverture du spreadsheet par ID depuis le SA                    |

**Note importante :** Les API Sheets et Drive doivent etre activees sur le projet GCP, meme si le SA a deja un acces `writer` sur le spreadsheet. Sans ces API activees, les appels echouent avec une erreur 403 depuis Cloud Run.

### Dockerfile

L'image est basee sur `python:3.12-slim`. Les dependances sont installees via `uv` (copie depuis `ghcr.io/astral-sh/uv:latest`). Seuls les fichiers source necessaires sont copies (pas de `.env`, `.git` ni `.venv`).

Le Dockerfile utilise `ENTRYPOINT` (et non `CMD`) pour permettre le passage d'arguments via `--args` lors de l'execution du Cloud Run Job. Par exemple, `--args="--check"` lance le health check au lieu du cycle normal.

---

## 8. Estimation des couts

### Palier gratuit GCP (Free Tier)

| Service              | Quota gratuit mensuel                   | Usage estime                          | Cout estime    |
|----------------------|-----------------------------------------|---------------------------------------|----------------|
| Cloud Run Jobs       | 240 000 vCPU-secondes + 450 000 GiB-s  | ~720 executions x ~30s = 21 600 s     | 0 $            |
| Cloud Scheduler      | 3 jobs gratuits                         | 1 job                                 | 0 $            |
| Secret Manager       | 10 000 acces gratuits                   | ~1 440 acces/mois (2 secrets x 720)   | 0 $            |
| Artifact Registry    | 500 Mo gratuits                         | ~150 Mo (1 image)                     | 0 $            |
| Cloud Build          | 120 min de build/jour                   | ~2-3 min par build                    | 0 $            |
| Google Sheets API    | Aucun cout direct                       | ~2 160 appels/mois                    | 0 $            |
| Telegram API         | Gratuit                                 | ~720 messages/mois                    | 0 $            |

### Compte de service et permissions

Le compte de service `flat-research@sandbox-hugo.iam.gserviceaccount.com` est utilise par le Cloud Run Job et le Cloud Scheduler.

**Roles IAM au niveau projet :**

| Role                          | Raison                                                      |
|-------------------------------|--------------------------------------------------------------|
| `roles/run.invoker`           | Permet au Scheduler de declencher le Cloud Run Job           |
| `roles/cloudscheduler.admin`  | Gestion du job Scheduler                                     |

**Acces aux secrets :**

| Secret                | Role                              |
|-----------------------|-----------------------------------|
| `telegram-bot-token`  | `roles/secretmanager.secretAccessor` |
| `telegram-chat-id`    | `roles/secretmanager.secretAccessor` |

**Acces au Google Sheet :**

Le SA doit etre ajoute en tant que `writer` (editeur) directement sur le Google Sheet via le bouton Partager. Cela est independant des roles IAM GCP. Les API `sheets.googleapis.com` et `drive.googleapis.com` doivent aussi etre activees sur le projet.

### Calcul detaille

**Cloud Run Jobs :**

- 24 executions/jour x 30 jours = 720 executions/mois
- Chaque execution : ~30 secondes, 1 vCPU, 512 Mi RAM
- vCPU : 720 x 30 = 21 600 vCPU-s (quota : 240 000)
- Memoire : 720 x 30 x 0.5 = 10 800 GiB-s (quota : 450 000)

**Verdict : le projet fonctionne entierement dans le palier gratuit de GCP.** Les quotas sont utilises a moins de 10 % de leur capacite. Le seul risque de depassement serait un nombre anormalement eleve de builds Cloud Build dans une meme journee.
