# Flat Research - Guide d'utilisation

## Table des matieres

1. [Introduction](#introduction)
2. [Prerequis](#prerequis)
3. [Installation locale](#installation-locale)
4. [Configuration des criteres](#configuration-des-criteres)
5. [Utilisation](#utilisation)
6. [Deploiement sur Google Cloud (optionnel)](#deploiement-sur-google-cloud-optionnel)
7. [Depannage](#depannage)
8. [Modifier les criteres](#modifier-les-criteres)

---

## Introduction

Flat Research est un outil qui cherche automatiquement des appartements et des maisons a louer (ou a acheter) a Montreal. Il parcourt les sites Kijiji et Centris, filtre les annonces selon vos criteres (quartier, prix, nombre de chambres, etc.), puis :

- Enregistre les resultats dans un Google Sheet (un tableur en ligne) pour que vous puissiez les consulter facilement.
- Vous envoie une notification Telegram a chaque fois qu'une **nouvelle** annonce correspond a vos criteres.

L'outil detecte les doublons : si une annonce a deja ete enregistree dans le Google Sheet, elle ne sera pas ajoutee une deuxieme fois et vous ne recevrez pas de notification en double.

Vous pouvez lancer l'outil manuellement, le programmer pour qu'il s'execute toutes les heures sur votre ordinateur, ou le deployer sur Google Cloud pour qu'il tourne en continu sans que votre ordinateur soit allume.

---

## Prerequis

Avant de commencer, assurez-vous d'avoir les elements suivants :

| Element | Description |
|---------|-------------|
| **Python 3** | Le langage de programmation utilise par l'outil. Verifiez avec `python3 --version` dans votre terminal. |
| **uv** | Un gestionnaire de paquets Python rapide. Installez-le en suivant les instructions sur [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/). |
| **gcloud CLI** | L'outil en ligne de commande de Google Cloud. Necessaire pour acceder a Google Sheets. Installez-le depuis [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install). |
| **Un compte Telegram** | Pour recevoir les notifications sur votre telephone. Telechargez Telegram depuis votre App Store si ce n'est pas deja fait. |

---

## Installation locale

### Etape 1 : Telecharger le projet

Telechargez ou clonez le projet sur votre ordinateur. Si vous utilisez Git :

```bash
git clone <URL_DU_DEPOT>
cd flat-research
```

Si vous avez recu le projet sous forme de fichier ZIP, decompressez-le et ouvrez un terminal dans le dossier `flat-research`.

### Etape 2 : Lancer le script d'installation

Dans le terminal, executez :

```bash
bash setup.sh
```

Ce script installe automatiquement toutes les dependances Python necessaires via `uv sync`.

### Etape 3 : Configurer l'acces a Google Sheets

L'outil utilise Google Sheets pour stocker les annonces trouvees. Pour lui donner acces a votre Google Sheet, suivez ces etapes :

**a) Connectez-vous a votre compte Google via gcloud :**

```bash
gcloud auth login
```

Une fenetre de navigateur va s'ouvrir. Connectez-vous avec votre compte Google.

**b) Configurez les "Application Default Credentials" (ADC) avec impersonation d'un compte de service :**

```bash
gcloud auth application-default login \
  --impersonate-service-account=VOTRE_SERVICE_ACCOUNT@VOTRE_PROJET.iam.gserviceaccount.com
```

Remplacez `VOTRE_SERVICE_ACCOUNT@VOTRE_PROJET.iam.gserviceaccount.com` par l'adresse du compte de service qui vous a ete communiquee. Cette commande va ouvrir votre navigateur pour vous authentifier.

**c) Activez les APIs necessaires dans votre projet Google Cloud :**

```bash
gcloud services enable sheets.googleapis.com drive.googleapis.com
```

**d) Partagez le Google Sheet avec le compte de service :**

Ouvrez votre Google Sheet dans le navigateur, cliquez sur le bouton "Partager" en haut a droite, et ajoutez l'adresse du compte de service (par exemple `flat-research@sandbox-hugo.iam.gserviceaccount.com`) en tant qu'editeur.

### Etape 4 : Configurer le bot Telegram

Le bot Telegram vous enverra des notifications quand de nouvelles annonces sont trouvees.

**a) Creer le bot :**

1. Ouvrez Telegram sur votre telephone ou votre ordinateur.
2. Recherchez `@BotFather` dans la barre de recherche et ouvrez la conversation.
3. Envoyez la commande `/newbot`.
4. BotFather vous demandera un nom pour le bot (par exemple : `Flat Research Montreal`).
5. BotFather vous demandera un identifiant unique qui doit se terminer par `bot` (par exemple : `flat_research_mtl_bot`).
6. BotFather vous donnera un **token** qui ressemble a ceci : `8626877634:AAGiUJ_ZQoRHI3glzKTjwratt_PRnoCHud4`. Notez-le precieusement.

**b) Obtenir votre chat_id (pour les notifications personnelles) :**

1. Ouvrez une conversation avec votre nouveau bot dans Telegram et envoyez-lui un message quelconque (par exemple : `bonjour`).
2. Dans votre navigateur, ouvrez l'URL suivante en remplacant `VOTRE_TOKEN` par le token obtenu a l'etape precedente :

```
https://api.telegram.org/botVOTRE_TOKEN/getUpdates
```

3. Vous verrez une reponse en format JSON. Cherchez le champ `"chat":{"id":` suivi d'un nombre. Ce nombre est votre **chat_id**.

### Etape 5 : Configurer les notifications de groupe (optionnel)

Si vous souhaitez recevoir les notifications dans un groupe Telegram (par exemple pour partager avec votre conjoint(e) ou colocataires) :

1. Creez un nouveau groupe dans Telegram.
2. Ajoutez votre bot au groupe (cherchez-le par son identifiant).
3. Envoyez un message dans le groupe.
4. Ouvrez l'URL suivante dans votre navigateur :

```
https://api.telegram.org/botVOTRE_TOKEN/getUpdates
```

5. Cherchez le `chat_id` du groupe. **Attention** : les identifiants de groupe sont des nombres **negatifs** (par exemple : `-5261793367`). C'est normal.

### Etape 6 : Remplir le fichier .env

Ouvrez le fichier `.env` a la racine du projet avec un editeur de texte et remplissez-le avec vos informations :

```
TELEGRAM_BOT_TOKEN=votre_token_ici
TELEGRAM_CHAT_ID=votre_chat_id_ici
```

Par exemple :

```
TELEGRAM_BOT_TOKEN=8626877634:AAGiUJ_ZQoRHI3glzKTjwratt_PRnoCHud4
TELEGRAM_CHAT_ID=-5261793367
```

Si vous utilisez un groupe, mettez le chat_id du groupe (nombre negatif). Si vous voulez des notifications personnelles, mettez votre chat_id personnel (nombre positif).

---

## Configuration des criteres

Les criteres de recherche se trouvent dans le fichier `config.yaml` a la racine du projet. Voici une explication de chaque champ :

### Section `criteria`

| Champ | Description | Exemple |
|-------|-------------|---------|
| `city` | La ville dans laquelle chercher. | `"Montreal"` |
| `type` | Le type de recherche : `location` pour louer, `achat` pour acheter. | `"location"` |
| `property_type` | Les types de propriete a inclure. Valeurs possibles : `appartement`, `maison`. Vous pouvez en mettre plusieurs. | `- appartement` |
| `neighbourhoods` | La liste des quartiers a surveiller. Un quartier par ligne, precede de `- `. | `- Villeray` |
| `bedrooms_min` | Le nombre minimum de chambres. | `3` |
| `price_min` | Le prix minimum (en dollars par mois pour une location, en dollars pour un achat). | `2000` |
| `price_max` | Le prix maximum. | `3000` |
| `furnished` | `true` si vous cherchez un logement meuble, `false` sinon. | `true` |
| `parking` | `true` si vous avez besoin d'un stationnement, `false` sinon. | `true` |

**A propos de la notation quebecoise des pieces :**

Au Quebec, les annonces utilisent souvent une notation comme 3 1/2, 4 1/2, 5 1/2, etc. Le "1/2" represente la salle de bain. Voici la correspondance avec le nombre de chambres :

| Notation quebecoise | Pieces | Chambres |
|---------------------|--------|----------|
| 3 1/2 | Salon + cuisine + 1 chambre + salle de bain | 1 chambre |
| 4 1/2 | Salon + cuisine + 2 chambres + salle de bain | 2 chambres |
| 5 1/2 | Salon + cuisine + 3 chambres + salle de bain | 3 chambres |
| 6 1/2 | Salon + cuisine + 4 chambres + salle de bain | 4 chambres |

Donc si vous cherchez un 5 1/2, mettez `bedrooms_min: 3` dans la configuration.

### Section `sources`

La liste des sites a parcourir. Valeurs possibles : `kijiji`, `centris`.

```yaml
sources:
  - kijiji
  - centris
```

### Section `google_sheets`

| Champ | Description |
|-------|-------------|
| `spreadsheet_name` | Le nom du Google Sheet (pour reference). |
| `spreadsheet_id` | L'identifiant unique du Google Sheet. Vous le trouvez dans l'URL du Sheet : `https://docs.google.com/spreadsheets/d/IDENTIFIANT_ICI/edit`. |

### Section `telegram`

Ces valeurs sont chargees automatiquement depuis le fichier `.env`. Vous n'avez pas besoin de les modifier dans `config.yaml`.

### Section `schedule`

| Champ | Description |
|-------|-------------|
| `interval_minutes` | L'intervalle en minutes entre chaque recherche (utilise avec l'option `--schedule`). |

---

## Utilisation

### Lancer une seule recherche

Pour lancer l'outil une seule fois :

```bash
uv run python main.py
```

L'outil va :
1. Parcourir Kijiji et Centris en parallele.
2. Filtrer les annonces selon vos criteres.
3. Ajouter les nouvelles annonces au Google Sheet.
4. Vous envoyer une notification Telegram pour chaque nouvelle annonce.

### Lancer en mode programme (continu)

Pour que l'outil tourne en boucle et cherche automatiquement selon l'intervalle defini dans `config.yaml` (par defaut toutes les 60 minutes) :

```bash
uv run python main.py --schedule
```

Cette commande bloque le terminal : l'outil tourne tant que vous ne l'arretez pas (avec Ctrl+C).

### Programmer une execution automatique avec cron

Si vous voulez que l'outil s'execute automatiquement toutes les heures, meme quand vous ne l'utilisez pas (tant que votre ordinateur est allume), utilisez `cron` :

1. Ouvrez l'editeur de cron :

```bash
crontab -e
```

2. Ajoutez la ligne suivante (en adaptant le chemin vers votre dossier de projet) :

```
0 * * * * cd /Users/hugboron/Documents/flat-research && uv run python main.py >> flat-research.log 2>&1
```

Cette ligne signifie : "a la minute 0 de chaque heure, lancer l'outil et ecrire les logs dans le fichier `flat-research.log`".

3. Sauvegardez et fermez l'editeur.

### Consulter le Google Sheet

Ouvrez le Google Sheet dans votre navigateur. Vous y trouverez toutes les annonces trouvees, avec les informations suivantes pour chaque annonce : titre, prix, quartier, nombre de chambres, lien vers l'annonce, date de decouverte, etc.

### Que se passe-t-il quand l'outil tourne ?

- **Nouvelles annonces** : Elles sont ajoutees au Google Sheet et vous recevez une notification Telegram.
- **Annonces deja connues (doublons)** : L'outil les detecte automatiquement et les ignore. Vous ne recevez pas de notification en double et elles ne sont pas ajoutees une deuxieme fois au Sheet.
- **Aucune annonce trouvee** : Un message "No matching listings found this cycle." apparait dans les logs. Aucune notification n'est envoyee.

---

## Deploiement sur Google Cloud (optionnel)

Cette section est destinee aux utilisateurs qui souhaitent que l'outil tourne automatiquement dans le cloud, sans avoir besoin de laisser leur ordinateur allume. Le deploiement utilise Google Cloud Run Jobs et Cloud Scheduler.

### Prerequis

- Un compte Google Cloud avec un **compte de facturation actif** (billing account).
- Le `gcloud CLI` installe et configure sur votre ordinateur.
- Etre connecte a gcloud :

```bash
gcloud auth login
gcloud config set project sandbox-hugo
```

### Lancer le deploiement

Depuis le dossier du projet, executez :

```bash
./deploy.sh
```

Ce script effectue les operations suivantes automatiquement :

1. **Active les APIs necessaires** : Cloud Run, Artifact Registry, Cloud Scheduler, Secret Manager.
2. **Configure les permissions** du compte de service.
3. **Cree un depot d'images Docker** dans Artifact Registry (region Montreal).
4. **Construit et publie l'image Docker** de l'application via Cloud Build.
5. **Stocke vos secrets Telegram** (bot token et chat_id) dans Secret Manager, de maniere securisee.
6. **Cree un Cloud Run Job** qui execute l'application avec les secrets injectes.
7. **Cree un Cloud Scheduler** qui declenche le job automatiquement toutes les heures (a la 17e minute de chaque heure).

A la fin du deploiement, le script affiche les liens vers la console Google Cloud pour visualiser le job et le scheduler.

### Tester manuellement

Pour lancer le job une seule fois dans le cloud (sans attendre le scheduler) :

```bash
gcloud run jobs execute flat-research --region=northamerica-northeast1 --project=sandbox-hugo
```

### Consulter les logs

Pour voir les logs d'execution du job :

```bash
gcloud run jobs executions list --job=flat-research --region=northamerica-northeast1 --project=sandbox-hugo
```

Pour voir les logs detailles d'une execution specifique :

```bash
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=flat-research" --project=sandbox-hugo --limit=50 --format="table(timestamp,textPayload)"
```

Vous pouvez aussi consulter les logs directement dans la console Google Cloud :
[https://console.cloud.google.com/run/jobs/details/northamerica-northeast1/flat-research?project=sandbox-hugo](https://console.cloud.google.com/run/jobs/details/northamerica-northeast1/flat-research?project=sandbox-hugo)

### Arreter ou supprimer

**Arreter les executions programmees** (desactiver le scheduler sans tout supprimer) :

```bash
gcloud scheduler jobs pause flat-research-schedule --location=northamerica-northeast1 --project=sandbox-hugo
```

Pour le reactiver plus tard :

```bash
gcloud scheduler jobs resume flat-research-schedule --location=northamerica-northeast1 --project=sandbox-hugo
```

**Supprimer completement** le job et le scheduler :

```bash
gcloud scheduler jobs delete flat-research-schedule --location=northamerica-northeast1 --project=sandbox-hugo
gcloud run jobs delete flat-research --region=northamerica-northeast1 --project=sandbox-hugo
```

---

## Depannage

### "ADC not configured" ou "Application Default Credentials"

Ce message signifie que l'outil n'arrive pas a s'authentifier aupres de Google Sheets. Lancez la commande suivante :

```bash
gcloud auth application-default login \
  --impersonate-service-account=flat-research@sandbox-hugo.iam.gserviceaccount.com
```

Puis relancez l'outil.

### "Spreadsheet not found" ou "Permission denied" pour Google Sheets

Le Google Sheet n'est pas accessible. Verifiez que :

1. L'identifiant (`spreadsheet_id`) dans `config.yaml` est correct.
2. Le Google Sheet est partage avec le compte de service. Ouvrez le Sheet, cliquez "Partager", et ajoutez `flat-research@sandbox-hugo.iam.gserviceaccount.com` en tant qu'editeur.

### "Telegram 400 error" ou erreur d'envoi de notification

Ce probleme vient generalement d'un token ou d'un chat_id incorrect. Verifiez :

1. Que le `TELEGRAM_BOT_TOKEN` dans le fichier `.env` est correct (copiez-le a nouveau depuis BotFather si necessaire).
2. Que le `TELEGRAM_CHAT_ID` dans le fichier `.env` est correct.
3. Que vous avez envoye au moins un message a votre bot avant de lancer l'outil (sinon le bot ne peut pas vous ecrire).
4. Si vous utilisez un groupe, verifiez que le bot a bien ete ajoute au groupe et que le chat_id est negatif.

### "No matching listings found" (aucune annonce trouvee)

Cela signifie qu'aucune annonce ne correspond a vos criteres actuels. Essayez de :

- Augmenter le `price_max` (budget plus eleve).
- Reduire le `bedrooms_min` (moins de chambres).
- Ajouter des quartiers dans la liste `neighbourhoods`.
- Mettre `furnished: false` si vous n'avez pas besoin d'un logement meuble.
- Mettre `parking: false` si le stationnement n'est pas obligatoire.

---

## Modifier les criteres

Pour changer vos criteres de recherche, ouvrez le fichier `config.yaml` avec un editeur de texte.

### Changer les quartiers

Modifiez la liste sous `neighbourhoods`. Ajoutez ou retirez des quartiers selon vos preferences :

```yaml
neighbourhoods:
  - Villeray
  - Mile-Ex
  - Petite-Patrie
  - Rosemont
  - Plateau-Mont-Royal
  - Hochelaga
```

### Changer le budget

Modifiez les valeurs `price_min` et `price_max` :

```yaml
price_min: 1500
price_max: 2500
```

### Changer le nombre de chambres

Modifiez la valeur `bedrooms_min`. Rappelez-vous la correspondance avec la notation quebecoise :

```yaml
bedrooms_min: 2    # Correspond a un 4 1/2
```

### Passer de location a achat

Changez la valeur de `type` :

```yaml
type: "achat"
```

Les valeurs `price_min` et `price_max` deviennent alors le prix d'achat en dollars (et non plus le loyer mensuel).

### Changer les sources

Pour ne chercher que sur un seul site :

```yaml
sources:
  - kijiji
```

Ou pour chercher sur les deux :

```yaml
sources:
  - kijiji
  - centris
```

### Changer la frequence de recherche

Modifiez la valeur `interval_minutes` dans la section `schedule` :

```yaml
schedule:
  interval_minutes: 30   # Chercher toutes les 30 minutes
```

Cette valeur est utilisee uniquement avec l'option `--schedule`. Si vous utilisez `cron`, modifiez plutot la ligne dans `crontab -e`. Par exemple, pour toutes les 30 minutes :

```
*/30 * * * * cd /Users/hugboron/Documents/flat-research && uv run python main.py >> flat-research.log 2>&1
```

---

Apres toute modification du fichier `config.yaml`, il suffit de relancer l'outil pour que les nouveaux criteres soient pris en compte. Aucune reinstallation n'est necessaire.

Si l'outil est deploye sur Google Cloud, vous devez relancer `./deploy.sh` apres avoir modifie `config.yaml` pour que les changements soient pris en compte dans le cloud.
