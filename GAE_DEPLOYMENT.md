# FoodBridge — Google App Engine Deployment Guide

## Overview

This guide walks you through deploying the FoodBridge application to **Google App Engine (Standard Environment)** with **Cloud SQL (MySQL)** as the database and **Google Cloud Storage (GCS)** for image uploads.

---

## Prerequisites Checklist

| Requirement | Check |
|-------------|-------|
| Google account | ✅ |
| Google Cloud project created | ✅ |
| Billing enabled on GCP project | ✅ |
| Google Cloud SDK (`gcloud`) installed | ✅ |
| Python 3.10+ installed locally | ✅ |

---

## PHASE 1 — Install Google Cloud SDK

### Windows

1. Download the installer: https://cloud.google.com/sdk/docs/install
2. Run the installer and follow the wizard
3. Open a **new PowerShell window** and verify:

```powershell
gcloud --version
```

Expected output:
```
Google Cloud SDK 480.x.x
...
```

---

## PHASE 2 — GCP Project Setup

### Step 1 — Authenticate

```powershell
gcloud auth login
```

A browser window opens. Sign in with your Google account.

### Step 2 — Create or Select a Project

```powershell
# Create new project
gcloud projects create foodbridge-app-001 --name="FoodBridge"

# OR use existing project
gcloud config set project YOUR_EXISTING_PROJECT_ID
```

### Step 3 — Enable Required APIs

```powershell
gcloud services enable appengine.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### Step 4 — Initialize App Engine (only once per project)

```powershell
gcloud app create --region=asia-south1
```

> Recommended region: `asia-south1` (Mumbai) for India-based projects.

---

## PHASE 3 — Cloud SQL (MySQL) Setup

### Step 1 — Create Cloud SQL Instance

```powershell
gcloud sql instances create foodbridge-db `
  --database-version=MYSQL_8_0 `
  --tier=db-f1-micro `
  --region=asia-south1 `
  --storage-auto-increase
```

> `db-f1-micro` is the free-tier eligible instance. Takes ~5 minutes to create.

### Step 2 — Create the Database

```powershell
gcloud sql databases create food_donation_prod `
  --instance=foodbridge-db
```

### Step 3 — Create a Database User

```powershell
gcloud sql users create foodbridge_user `
  --instance=foodbridge-db `
  --password=YOUR_STRONG_PASSWORD
```

### Step 4 — Get the Connection Name

```powershell
gcloud sql instances describe foodbridge-db --format="value(connectionName)"
```

Note this value — it looks like: `your-project-id:asia-south1:foodbridge-db`

---

## PHASE 4 — Cloud Storage (GCS) Setup

### Step 1 — Create a GCS Bucket

```powershell
gcloud storage buckets create gs://foodbridge-uploads-001 `
  --location=ASIA-SOUTH1 `
  --uniform-bucket-level-access
```

### Step 2 — Make Bucket Publicly Readable (for food images)

```powershell
gcloud storage buckets add-iam-policy-binding gs://foodbridge-uploads-001 `
  --member=allUsers `
  --role=roles/storage.objectViewer
```

---

## PHASE 5 — Update app.yaml

Open [app.yaml](file:///c:/Users/Shiyam%20S/Downloads/cloud%20mini/cloud%20mini/app.yaml) and replace the placeholder values:

```yaml
env_variables:
  FLASK_ENV: "production"
  SECRET_KEY: "your-very-long-random-secret-key-here"
  DB_USER: "foodbridge_user"
  DB_PASS: "YOUR_STRONG_PASSWORD"
  DB_NAME: "food_donation_prod"
  CLOUD_SQL_CONNECTION_NAME: "your-project-id:asia-south1:foodbridge-db"
  GOOGLE_CLOUD_PROJECT: "your-project-id"
  GCS_BUCKET_NAME: "foodbridge-uploads-001"

beta_settings:
  cloud_sql_instances: "your-project-id:asia-south1:foodbridge-db"
```

> **IMPORTANT:** Never commit `app.yaml` with real credentials to Git.
> Use [GCP Secret Manager](https://cloud.google.com/secret-manager) for production secrets.

---

## PHASE 6 — Initialize the Production Database

Before deploying, run the database migration to create tables in Cloud SQL:

```powershell
# Connect to Cloud SQL via Cloud SQL Proxy
# Install proxy:
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.11.0/cloud-sql-proxy.windows.amd64.exe

# Run proxy (keep this terminal open):
.\cloud-sql-proxy YOUR_PROJECT:asia-south1:foodbridge-db --port 3306

# In a NEW terminal, run the migration:
$env:DATABASE_URL = "mysql+pymysql://foodbridge_user:YOUR_PASSWORD@127.0.0.1:3306/food_donation_prod"
$env:FLASK_ENV    = "production"
.\venv\Scripts\python.exe -c "
from app import create_app
from app.extensions import db
app = create_app()
with app.app_context():
    db.create_all()
    print('Tables created successfully!')
"
```

---

## PHASE 7 — Deploy to App Engine

```powershell
# Navigate to project folder
cd "c:\Users\Shiyam S\Downloads\cloud mini\cloud mini"

# Deploy
gcloud app deploy app.yaml --quiet
```

> First deployment takes **3–5 minutes** (builds Docker image and uploads files).

---

## PHASE 8 — Verify Deployment

### Option A — Open in Browser

```powershell
gcloud app browse
```

### Option B — Run the Verification Script (Local)

```powershell
.\venv\Scripts\python.exe verify_deployment.py --url http://127.0.0.1:5000
```

### Option C — Run the Verification Script (GAE)

```powershell
.\venv\Scripts\python.exe verify_deployment.py --url https://YOUR_PROJECT_ID.appspot.com
```

Expected output:
```
  [PASS] Home page                                 HTTP 200
  [PASS] About page                                HTTP 200
  [PASS] Login page                                HTTP 200
  [PASS] Register page                             HTTP 200
  [PASS] API donations list                        HTTP 200
  [PASS] API nearby donations                      HTTP 200
  [PASS] API dashboard stats                       HTTP 200
  [PASS] Donor dashboard                           HTTP 302
  [PASS] NGO dashboard                             HTTP 302
  [PASS] Admin dashboard                           HTTP 302
  [PASS] 404 page                                  HTTP 404

  RESULT : 11/11 checks passed
  STATUS : DEPLOYMENT IS HEALTHY!
```

### Option D — Check App Engine Logs

```powershell
gcloud app logs tail -s default
```

---

## PHASE 9 — View Deployment in GCP Console

| Section | URL |
|---------|-----|
| App Engine Dashboard | https://console.cloud.google.com/appengine |
| Deployed Versions | https://console.cloud.google.com/appengine/versions |
| Live App Logs | https://console.cloud.google.com/appengine/logs |
| Cloud SQL | https://console.cloud.google.com/sql |
| Cloud Storage | https://console.cloud.google.com/storage |

---

## Deployment Files Summary

| File | Purpose |
|------|---------|
| [app.yaml](file:///c:/Users/Shiyam%20S/Downloads/cloud%20mini/cloud%20mini/app.yaml) | GAE runtime, scaling, env variables, routes |
| [.gcloudignore](file:///c:/Users/Shiyam%20S/Downloads/cloud%20mini/cloud%20mini/.gcloudignore) | Excludes venv, DB, uploads, tests from upload |
| [verify_deployment.py](file:///c:/Users/Shiyam%20S/Downloads/cloud%20mini/cloud%20mini/verify_deployment.py) | Endpoint health check after deploy |
| [requirements.txt](file:///c:/Users/Shiyam%20S/Downloads/cloud%20mini/cloud%20mini/requirements.txt) | Dependencies (GAE auto-installs these) |
| [app.py](file:///c:/Users/Shiyam%20S/Downloads/cloud%20mini/cloud%20mini/app.py) | Entry point (`app` object used by gunicorn) |

---

## Quick Commands Reference

```powershell
# Deploy
gcloud app deploy

# View live app
gcloud app browse

# View logs
gcloud app logs tail -s default

# List versions
gcloud app versions list

# Rollback to previous version
gcloud app versions migrate PREVIOUS_VERSION_ID

# Stop a version
gcloud app versions stop VERSION_ID
```

---

## Estimated GCP Costs (Free Tier)

| Resource | Free Tier |
|----------|-----------|
| App Engine F2 instances | 28 instance-hours/day free |
| Cloud SQL db-f1-micro | Not free (~$7/month) |
| Cloud Storage | 5 GB free |
| Egress | 1 GB/month free |

> For zero cost during testing: use **SQLite in App Engine** by not configuring Cloud SQL. The app will auto-fall back to SQLite. Note: SQLite is ephemeral on GAE (resets on redeploy).
