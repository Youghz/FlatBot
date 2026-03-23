terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ─── APIs ───────────────────────────────────────────────────────────

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudscheduler.googleapis.com",
    "secretmanager.googleapis.com",
    "sqladmin.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# ─── Artifact Registry ──────────────────────────────────────────────

resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "flat-research"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

# ─── Cloud SQL ──────────────────────────────────────────────────────

resource "random_password" "db_password" {
  length  = 32
  special = false
  count   = var.db_password == "" ? 1 : 0
}

locals {
  db_password = var.db_password != "" ? var.db_password : random_password.db_password[0].result
  db_connection = "${var.project_id}:${var.region}:${google_sql_database_instance.db.name}"
  database_url  = "postgresql://postgres:${local.db_password}@/${google_sql_database.flatbot.name}?host=/cloudsql/${local.db_connection}"
}

resource "google_sql_database_instance" "db" {
  name             = "flatbot-db"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = "db-f1-micro"
    disk_autoresize   = true
    availability_type = "ZONAL"

    ip_configuration {
      ipv4_enabled = true  # Needed for Cloud Run without VPC connector
    }
  }

  deletion_protection = true
  depends_on          = [google_project_service.apis]
}

resource "google_sql_database" "flatbot" {
  name     = "flatbot"
  instance = google_sql_database_instance.db.name
}

resource "google_sql_user" "postgres" {
  name     = "postgres"
  instance = google_sql_database_instance.db.name
  password = local.db_password
}

# ─── Secrets ────────────────────────────────────────────────────────

resource "random_password" "jwt_secret" {
  length  = 64
  special = false
  count   = var.jwt_secret_key == "" ? 1 : 0
}

locals {
  jwt_secret_key = var.jwt_secret_key != "" ? var.jwt_secret_key : random_password.jwt_secret[0].result
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "database-url"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = local.database_url
}

resource "google_secret_manager_secret" "jwt_secret_key" {
  secret_id = "jwt-secret-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "jwt_secret_key" {
  secret      = google_secret_manager_secret.jwt_secret_key.id
  secret_data = local.jwt_secret_key
}

resource "google_secret_manager_secret" "telegram_bot_token" {
  secret_id = "telegram-bot-token"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "telegram_bot_token" {
  secret      = google_secret_manager_secret.telegram_bot_token.id
  secret_data = var.telegram_bot_token
}

# ─── Service Account ───────────────────────────────────────────────

resource "google_service_account" "flatbot" {
  account_id   = "flatbot"
  display_name = "FlatBot Service Account"
}

resource "google_project_iam_member" "flatbot_roles" {
  for_each = toset([
    "roles/run.invoker",
    "roles/cloudscheduler.admin",
    "roles/cloudsql.client",
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.flatbot.email}"
}

resource "google_secret_manager_secret_iam_member" "access" {
  for_each = {
    database_url      = google_secret_manager_secret.database_url.id
    jwt_secret_key    = google_secret_manager_secret.jwt_secret_key.id
    telegram_bot_token = google_secret_manager_secret.telegram_bot_token.id
  }
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.flatbot.email}"
}

# ─── Cloud Run Service (web) ───────────────────────────────────────

locals {
  web_image     = "${var.region}-docker.pkg.dev/${var.project_id}/flat-research/flatbot-web:latest"
  scraper_image = "${var.region}-docker.pkg.dev/${var.project_id}/flat-research/flatbot-scraper:latest"
  secrets_env = {
    DATABASE_URL      = "${google_secret_manager_secret.database_url.id}/versions/latest"
    JWT_SECRET_KEY    = "${google_secret_manager_secret.jwt_secret_key.id}/versions/latest"
    TELEGRAM_BOT_TOKEN = "${google_secret_manager_secret.telegram_bot_token.id}/versions/latest"
  }
}

resource "google_cloud_run_v2_service" "web" {
  name     = "flatbot-web"
  location = var.region

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [local.db_connection]
      }
    }

    containers {
      image = local.web_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          memory = "512Mi"
        }
      }

      dynamic "env" {
        for_each = local.secrets_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }

    service_account = google_service_account.flatbot.email
  }

  depends_on = [
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.jwt_secret_key,
    google_secret_manager_secret_version.telegram_bot_token,
  ]

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,  # Image updated by CI/CD
    ]
  }
}

# Allow unauthenticated access to the web service
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.web.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ─── Cloud Run Job (scraper) ──────────────────────────────────────

resource "google_cloud_run_v2_job" "scraper" {
  name     = "flatbot-scraper"
  location = var.region

  template {
    template {
      timeout     = "300s"
      max_retries = 1

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [local.db_connection]
        }
      }

      containers {
        image = local.scraper_image

        resources {
          limits = {
            memory = "512Mi"
          }
        }

        dynamic "env" {
          for_each = local.secrets_env
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value
                version = "latest"
              }
            }
          }
        }

        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
      }

      service_account = google_service_account.flatbot.email
    }
  }

  depends_on = [
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.jwt_secret_key,
    google_secret_manager_secret_version.telegram_bot_token,
  ]

  lifecycle {
    ignore_changes = [
      template[0].template[0].containers[0].image,  # Image updated by CI/CD
    ]
  }
}

# ─── Cloud Scheduler (hourly scrape) ──────────────────────────────

resource "google_cloud_scheduler_job" "scraper" {
  name     = "flatbot-scraper-schedule"
  region   = var.region
  schedule = "17 * * * *"  # Every hour at :17

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.scraper.name}:run"

    oauth_token {
      service_account_email = google_service_account.flatbot.email
    }
  }

  depends_on = [google_project_service.apis]
}
