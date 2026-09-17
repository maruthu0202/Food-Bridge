# FoodBridge — Complete Railway Deployment Guide

## Table of Contents
1. [What is Railway?](#1-what-is-railway)
2. [All Railway Services Explained](#2-all-railway-services-explained)
3. [Services We Are Using for FoodBridge](#3-services-we-are-using-for-foodbridge)
4. [Railway Free Tier — What You Get](#4-railway-free-tier--what-you-get)
5. [Pre-Deployment Checklist](#5-pre-deployment-checklist)
6. [Step-by-Step Deployment Guide](#6-step-by-step-deployment-guide)
7. [Environment Variables Reference](#7-environment-variables-reference)
8. [File Storage on Railway (Replacing GCS)](#8-file-storage-on-railway-replacing-gcs)
9. [Database Migration on Railway](#9-database-migration-on-railway)
10. [Connecting Custom Domain](#10-connecting-custom-domain)
11. [Monitoring and Logs](#11-monitoring-and-logs)
12. [Troubleshooting Common Issues](#12-troubleshooting-common-issues)
13. [Cost Breakdown](#13-cost-breakdown)

---

## 1. What is Railway?

Railway is a modern cloud platform that lets developers deploy applications and databases
in minutes without needing to configure servers, VMs, or complex cloud infrastructure.
It handles everything — from provisioning servers to managing databases — through a
simple dashboard and GitHub integration.

### Key Concepts

- Project     : A container that holds all your services (app + database + etc.)
- Service     : An individual deployable unit (your Flask app, a MySQL DB, a Redis cache, etc.)
- Environment : A context (Production, Staging) where services run with their own configs
- Variables   : Environment variables (secrets) injected into your running containers
- Deployments : Versioned snapshots of your service — Railway keeps a history of every deploy

### How Railway Works (Simplified)

  Your GitHub Repo
        |
        | (push to main branch)
        v
  Railway detects changes
        |
        | (auto-build using Nixpacks or Dockerfile)
        v
  Docker Container is built and started
        |
        | (PORT assigned automatically)
        v
  Your App is LIVE at a public HTTPS URL

Railway uses Nixpacks by default — it automatically detects Python projects,
installs your requirements.txt, and starts the server. No Dockerfile needed.

---

## 2. All Railway Services Explained

Railway offers the following categories of services. Here is every service they provide:

### 2.1 Web Services (App Hosting)
Deploy any web application from GitHub. Railway auto-detects the language/framework
and builds and runs your app.

- Supports: Python, Node.js, Ruby, Go, Java, PHP, Rust, .NET
- Auto-detects: Flask, Django, FastAPI, Express, Rails, Spring Boot
- Features: Auto-deploys on git push, rollback to previous versions, PR preview environments

### 2.2 MySQL (Database Service)
A fully managed MySQL 8.0 database.

- No setup required — one click to add
- Automatic daily backups (paid plans)
- Accessible via internal network (fast) or public URL (for tools like MySQL Workbench)
- Provides a DATABASE_URL environment variable automatically
- Persistent storage — data survives app restarts

### 2.3 PostgreSQL (Database Service)
A fully managed PostgreSQL 16 database.

- Same features as MySQL above
- Popular with Railway users because of strong ecosystem support

### 2.4 Redis (Cache / Message Broker)
A fully managed Redis 7 in-memory data store.

- Used for caching, session storage, rate limiting, Celery task queues
- Provides a REDIS_URL environment variable automatically

### 2.5 MongoDB (Database Service)
A fully managed MongoDB NoSQL database.

- Good for document-oriented data
- Provides a MONGODB_URL automatically

### 2.6 Static File Hosting
Serve static HTML/CSS/JS sites directly.

- No server needed — just point to your build output directory
- Global CDN distribution

### 2.7 Docker Service
Deploy any Docker image from Docker Hub or a private registry.

- Full control over the container environment
- Custom Dockerfile support

### 2.8 Cron Jobs
Run scheduled background tasks on a cron schedule (e.g., expire old donations every hour).

- Define cron expression (e.g., 0 * * * *)
- Runs a command in a temporary container on schedule

### 2.9 Volume (Persistent Storage)
Attach a persistent disk volume to a service.

- Data persists across deployments and restarts
- Used for file uploads, local SQLite databases, or any disk-based data

### 2.10 Private Networking
Services in the same Railway project can talk to each other on a private network
(no public internet required — faster and more secure).

- E.g., your Flask app connects to MySQL via internal hostname mysql.railway.internal

### 2.11 Observability (Logs and Metrics)
Built-in monitoring for all services:

- Real-time log streaming
- CPU and RAM usage graphs
- Request count tracking
- Deployment history and status

### 2.12 GitHub Integration
- Connect a GitHub repository
- Auto-deploy on every push to a branch
- Preview deployments for Pull Requests

---

## 3. Services We Are Using for FoodBridge

Based on your project analysis, here are exactly the Railway services used and why:

  FoodBridge on Railway
  ├── [SERVICE 1] Web Service     — Flask app (app.py + gunicorn)
  ├── [SERVICE 2] MySQL Database  — Replaces Google Cloud SQL
  └── [SERVICE 3] Volume          — For uploaded food images (replaces GCS)


### SERVICE 1 — Web Service (Flask App)

What it does: Hosts your Python/Flask application.

Railway detects your project as Python because:
- requirements.txt is present → it installs all dependencies
- gunicorn is in your requirements → Railway uses it as the server
- app.py is the entry point → Railway starts gunicorn app:app

Your existing gunicorn setup from app.yaml translates perfectly:
  app.yaml (Google Cloud):  gunicorn -b :$PORT -w 2 app:app
  Railway (auto-detected):  gunicorn -b :$PORT app:app

Railway provides the PORT environment variable automatically — your app already uses it.

What gets deployed:
- All routes (auth, donor, ngo, admin, api blueprints)
- All templates (Jinja2 HTML files)
- All static files (CSS, JS, images)
- All services (donation_service, pickup_service, matching_service, location_service)


### SERVICE 2 — MySQL Database

What it does: Replaces Google Cloud SQL with Railway's managed MySQL.

Your ProductionConfig in config.py supports a DATABASE_URL environment variable:

    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")   # Railway sets this automatically!
        or ...
    )

Railway MySQL gives you:
- Connection URL format: mysql+pymysql://user:pass@host:port/dbname
- Accessible from your Flask app via private network (low latency)
- PyMySQL (already in your requirements.txt) handles the connection

No code changes needed — just set DATABASE_URL in Railway variables.


### SERVICE 3 — Volume (Persistent File Storage)

What it does: Provides persistent disk storage for uploaded food images.

Your storage_service.py already has local file fallback:

    # When GCS_BUCKET_NAME is empty, it saves to LOCAL_UPLOAD_FOLDER
    self._use_gcs = bool(self._bucket_name)   # False if no GCS bucket

By attaching a Railway Volume to /app/uploads, uploaded images persist
across deployments. Without a volume, files would be wiped on every redeploy.

Alternative: Use Cloudinary (free 25GB) for image hosting — see Section 8.


### Services We Are NOT Using on Railway

  Service       | Reason
  --------------|-----------------------------------------------------------
  PostgreSQL    | We use MySQL (PyMySQL already in requirements.txt)
  Redis         | No caching or background task queue in FoodBridge
  MongoDB       | FoodBridge uses relational/SQL database with SQLAlchemy
  Cron Jobs     | No scheduled background tasks in current version
  Static Hosting| Flask serves static files (CSS/JS) directly via /static/


---

## 4. Railway Free Tier — What You Get

  Resource          | Free Tier Limit
  ------------------|----------------------------------------
  Monthly Credit    | $5 free credit per month
  RAM               | Up to 512 MB per service
  CPU               | Shared vCPU
  Bandwidth         | 100 GB outbound per month
  Build Minutes     | 500 minutes per month
  Environments      | Unlimited
  Services          | Unlimited (within credit budget)
  Custom Domain     | Free
  HTTPS/SSL         | Free (auto-provisioned)
  Sleep Mode        | Does NOT sleep (unlike Render free tier)


### Estimated Monthly Usage for FoodBridge

  Service              | Estimated Cost/Month
  ---------------------|---------------------
  Flask Web App        | ~$1.50 (512MB RAM)
  MySQL Database       | ~$1.00 (256MB RAM)
  Volume (1GB)         | ~$0.25
  TOTAL                | ~$2.75/month
  Free Credit          | $5.00/month
  Out of Pocket        | $0.00

The $5 free credit covers FoodBridge with room to spare!

---

## 5. Pre-Deployment Checklist

Complete these steps BEFORE deploying to Railway:

### Step A — Push Your Project to GitHub

Railway deploys from GitHub. Your project must be in a GitHub repository.

    cd "c:\Users\Shiyam S\Downloads\cloud mini\cloud mini"
    git init
    git add .
    git commit -m "Initial commit — FoodBridge app"

Then go to https://github.com/new and create a new repo, then:

    git remote add origin https://github.com/YOUR_USERNAME/foodbridge.git
    git branch -M main
    git push -u origin main


### Step B — Create a .gitignore File

Create a file named .gitignore in your project root:

    # Python
    venv/
    __pycache__/
    *.pyc
    *.pyo
    .pytest_cache/

    # Environment secrets — NEVER commit this
    .env

    # Local database — do NOT commit this
    *.db
    *.sqlite

    # Uploaded files — use cloud storage in production
    uploads/

    # IDE files
    .vscode/
    .idea/


### Step C — Verify requirements.txt

Ensure gunicorn is listed (it already is in your project):

    gunicorn==22.0.0    # Already in your requirements.txt — GOOD


### Step D — Create Procfile (Recommended)

Create a file named Procfile (no extension) in your project root:

    web: gunicorn -b 0.0.0.0:$PORT -w 2 --timeout 120 app:app

This tells Railway exactly how to start your app.


### Step E — Fix DATABASE_URL Format for PyMySQL

Railway provides MySQL URLs as:     mysql://user:pass@host:port/db
But Flask/SQLAlchemy needs:         mysql+pymysql://user:pass@host:port/db

Add this fix to app/config.py inside ProductionConfig:

    # Fix Railway MySQL URL format
    _db_url = os.environ.get("DATABASE_URL", "")
    if _db_url.startswith("mysql://"):
        _db_url = _db_url.replace("mysql://", "mysql+pymysql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url or (...)


---

## 6. Step-by-Step Deployment Guide

### PHASE 1 — Account Setup

Step 1: Go to https://railway.app

Step 2: Click "Start a New Project" → Sign up with GitHub
        Use your GitHub account for seamless repo access

Step 3: You will land on the Railway Dashboard


### PHASE 2 — Create a New Project

Step 4: Click "New Project" button (top right)

Step 5: Select "Deploy from GitHub repo"

Step 6: Authorize Railway to access your GitHub account when prompted

Step 7: Search for and select your foodbridge repository

Step 8: Railway will start an initial build immediately.
        DO NOT wait for it — we need to add the database first


### PHASE 3 — Add MySQL Database

Step 9:  In your Railway project, click "+ New" button

Step 10: Select "Database" → Select "MySQL"

Step 11: Railway creates a MySQL service in about 30 seconds

Step 12: Click on the MySQL service → go to "Variables" tab

         You will see these auto-generated variables:
           MYSQL_DATABASE        = railway
           MYSQL_HOST            = mysql.railway.internal
           MYSQL_PASSWORD        = (auto-generated)
           MYSQL_PORT            = 3306
           MYSQL_ROOT_PASSWORD   = (auto-generated)
           MYSQL_USER            = root
           DATABASE_URL          = mysql://root:PASS@mysql.railway.internal:3306/railway


### PHASE 4 — Configure Your Flask App Service

Step 13: Click on your Flask app service (the one from your GitHub repo)

Step 14: Go to the "Variables" tab

Step 15: Add the following variables one by one (click "Add Variable" for each):

           FLASK_ENV           = production
           SECRET_KEY          = (generate a long random string — see below)
           DATABASE_URL        = (paste the DATABASE_URL from your MySQL service)
           GCS_BUCKET_NAME     = (leave EMPTY — uses local storage)
           GOOGLE_CLOUD_PROJECT= (leave EMPTY)

         How to generate a SECRET_KEY — open PowerShell and run:
           python -c "import secrets; print(secrets.token_hex(32))"
         Copy the output and paste it as your SECRET_KEY value.

Step 16: Click "Deploy" to trigger a new deployment with these variables


### PHASE 5 — Initialize the Database

Step 17: Click on your Flask app service → Click "..." menu → "Open in Shell"

Step 18: In the shell, run:
           python -c "from app import create_app; app = create_app(); print('Tables created OK')"

         Your create_app() already calls db.create_all() which creates all
         tables automatically. Tables should already exist after first deploy!

Step 19 (Optional — Seed demo data):
           python seed.py


### PHASE 6 — Add Persistent Volume for File Uploads

Step 20: Click on your Flask app service → "Settings" tab

Step 21: Scroll to "Volumes" section → Click "Add Volume"

Step 22: Set the mount path to:    /app/uploads

Step 23: Set volume size to 1 GB (free within your credit budget)

Step 24: Click "Add" — Railway will redeploy with the volume attached

         Now uploaded food images persist across deployments!


### PHASE 7 — Get Your Public URL

Step 25: Click on your Flask app service → "Settings" tab

Step 26: Under "Networking" → Click "Generate Domain"

         Railway generates a free HTTPS URL like:
           https://foodbridge-production.up.railway.app

Step 27: Visit this URL — your FoodBridge app is LIVE!


### PHASE 8 — Enable Auto-Deploy

Step 28: Click on your Flask app service → "Settings" tab

Step 29: Under "Deploy" → Ensure "Auto Deploy" is enabled for your main branch

         Now every time you push to GitHub, Railway automatically redeploys!


---

## 7. Environment Variables Reference

Complete list of all environment variables for FoodBridge on Railway:

  Variable               | Value                         | Required | Notes
  -----------------------|-------------------------------|----------|--------------------------------
  FLASK_ENV              | production                    | YES      | Enables ProductionConfig
  SECRET_KEY             | Long random string (64 chars) | YES      | Flask session security
  DATABASE_URL           | MySQL URL from Railway        | YES      | Auto-provided by MySQL service
  GCS_BUCKET_NAME        | (leave empty)                 | NO       | Uses local volume for uploads
  GOOGLE_CLOUD_PROJECT   | (leave empty)                 | NO       | Not needed on Railway


### Linking MySQL Service Variables Automatically

Instead of copying DATABASE_URL manually, Railway can inject it automatically:

1. Click your Flask app service → "Variables" tab
2. Click "Add Variable Reference"
3. Select the MySQL service
4. Select DATABASE_URL
5. It is now injected automatically and updates if the DB URL changes


---

## 8. File Storage on Railway (Replacing GCS)

You have two options for handling food photo uploads on Railway:

### Option A — Railway Volume (Simplest, Recommended to Start)

Attach a persistent volume to /app/uploads (done in Step 20-24 above).

  PROS:
  - Free within your $5 credit
  - No code changes needed
  - storage_service.py already supports local storage fallback
  - Images persist across deployments

  CONS:
  - Files are NOT on a CDN (slightly slower image loading)
  - Volume is tied to one geographic region


### Option B — Cloudinary (Best for Production Scale)

Cloudinary offers 25GB free storage and a global CDN for media files.

Setup:
1. Sign up at https://cloudinary.com (free account)

2. Install Cloudinary:
     pip install cloudinary
   Add to requirements.txt:
     cloudinary==1.40.0

3. Add these Railway variables:
     CLOUDINARY_CLOUD_NAME = your_cloud_name
     CLOUDINARY_API_KEY    = your_api_key
     CLOUDINARY_API_SECRET = your_api_secret

4. Update storage_service.py to add a Cloudinary upload backend.

For starting out, Option A (Volume) is easiest — no code changes!


---

## 9. Database Migration on Railway

Your app uses Flask-Migrate (Alembic) for database schema changes.

### Initial Setup (First Deploy)

Your create_app() calls db.create_all() which creates all tables automatically.
This is sufficient for the initial deployment. No manual steps needed.

### Making Schema Changes Later

When you change your models (add a column, new table, etc.):

Step 1: On your local machine, generate a migration:
          flask db migrate -m "describe your change here"

Step 2: Review the generated migration file in migrations/versions/

Step 3: Commit and push:
          git add migrations/
          git commit -m "Add migration: describe your change"
          git push origin main

Step 4: Railway redeploys automatically. Run the migration via Railway shell:
          flask db upgrade


### Auto-Run Migrations on Deploy

Update your Procfile to run migrations automatically before starting gunicorn:

    web: flask db upgrade && gunicorn -b 0.0.0.0:$PORT -w 2 --timeout 120 app:app

This ensures the database schema is always up to date before the app starts.


---

## 10. Connecting Custom Domain

If you have a domain name (e.g., foodbridge.com), connect it for free on Railway.

Step 1: Click your Flask app service → "Settings" → "Networking"

Step 2: Under "Custom Domain", click "Add Custom Domain"

Step 3: Enter your domain (e.g., foodbridge.com or www.foodbridge.com)

Step 4: Railway gives you a CNAME record to add at your domain registrar:
          Type  : CNAME
          Name  : www (or @)
          Value : foodbridge-production.up.railway.app

Step 5: Add this DNS record at your domain registrar (GoDaddy, Namecheap, etc.)

Step 6: Wait 5–60 minutes for DNS propagation

Step 7: Railway automatically provisions an SSL certificate via Let's Encrypt

Your app is now live at https://www.foodbridge.com with HTTPS!


---

## 11. Monitoring and Logs

### Viewing Real-Time Logs

1. Click your Flask app service
2. Click the "Logs" tab
3. Logs stream in real time — every gunicorn request, Flask log message,
   SQLAlchemy query error, etc.

### Key Logs to Watch After Deploy

  Good signs (app started OK):
    [INFO] Starting gunicorn 22.0.0
    [INFO] Listening at: http://0.0.0.0:PORT
    [INFO] Booting worker with pid: 123

  Bad signs (errors to fix):
    ModuleNotFoundError: No module named 'xyz'   → Add to requirements.txt
    sqlalchemy.exc.OperationalError              → Check DATABASE_URL variable
    KeyError: 'SECRET_KEY'                       → Check environment variables


### Metrics Dashboard

1. Click your service → "Metrics" tab
2. View CPU usage, RAM usage, and network traffic over time


### Deployment History

1. Click your service → "Deployments" tab
2. See every deployment with timestamp, commit hash, and status
3. Click "Rollback" on any previous deployment to instantly revert


---

## 12. Troubleshooting Common Issues

### Issue 1: Build Fails — "No module named X"
Cause: Dependency missing from requirements.txt
Fix:   Add the missing package to requirements.txt and push again


### Issue 2: App Crashes — "sqlalchemy.exc.OperationalError"
Cause: DATABASE_URL is wrong or MySQL service is not running
Fix:
  1. Go to MySQL service → Check if it is running (green status)
  2. Go to Flask service → Variables → Verify DATABASE_URL format:
       mysql+pymysql://user:pass@host:port/dbname
     Note: Railway provides mysql:// — change to mysql+pymysql:// for PyMySQL!


### Issue 3: Static Files Not Loading (CSS/JS broken)
Cause: Flask is not serving static files correctly
Fix:   Ensure templates reference /static/css/main.css not a hardcoded path.
       Your app already handles this correctly.


### Issue 4: Uploaded Images Disappear After Redeploy
Cause: No persistent volume — container filesystem resets on each deploy
Fix:   Attach a Railway Volume to /app/uploads (see Step 20-24)


### Issue 5: "504 Gateway Timeout"
Cause: App taking too long to start or gunicorn worker timeout
Fix:   In your Procfile, increase the timeout:
         web: gunicorn -b 0.0.0.0:$PORT -w 2 --timeout 300 app:app


### Issue 6: CSRF Token Errors in Production
Cause: SESSION_COOKIE_SECURE = True requires HTTPS
Fix:   Ensure you access your app via the https:// URL, not http://
       Railway provides HTTPS by default, so this should work automatically.


### Issue 7: DATABASE_URL Format Mismatch
Railway provides:  mysql://root:pass@host:port/db
SQLAlchemy needs:  mysql+pymysql://root:pass@host:port/db

Fix — add this to app/config.py in ProductionConfig:

    _db_url = os.environ.get("DATABASE_URL", "")
    if _db_url.startswith("mysql://"):
        _db_url = _db_url.replace("mysql://", "mysql+pymysql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url or (...)


---

## 13. Cost Breakdown

### Free Tier ($5/month credit)

  Item                        | Usage Estimate  | Cost
  ----------------------------|-----------------|----------
  Flask Web App (512MB RAM)   | 24/7 uptime     | ~$1.50
  MySQL Database (256MB)      | 24/7 uptime     | ~$1.00
  Volume (1GB storage)        | Persistent      | ~$0.25
  Bandwidth (100GB/mo free)   | Included        | $0.00
  SSL Certificate             | Included        | $0.00
  Custom Domain               | Included        | $0.00
  MONTHLY TOTAL               |                 | ~$2.75
  FREE CREDIT                 |                 | $5.00
  OUT OF POCKET               |                 | $0.00

FoodBridge runs completely free within Railway's $5/month credit!

### If You Exceed the Free Credit

Cheapest paid plan is $20/month (Hobby plan) which gives:
- $20 credit (instead of $5)
- More storage and higher RAM/CPU limits
- Priority support


---

## Summary — Quick Reference

  Railway Services Used by FoodBridge:
    [YES] Web Service   — Hosts Flask app with gunicorn
    [YES] MySQL         — Managed production database (replaces Google Cloud SQL)
    [YES] Volume        — Persistent file storage for food photo uploads

  Railway Services NOT Used:
    [NO] PostgreSQL     — We use MySQL (PyMySQL already in requirements.txt)
    [NO] Redis          — No caching or background tasks in FoodBridge
    [NO] MongoDB        — We use relational SQL with SQLAlchemy ORM
    [NO] Cron Jobs      — No scheduled background tasks in current version
    [NO] Static Hosting — Flask serves static files directly

  Deployment Trigger:
    git push origin main  -->  Railway auto-deploys in about 2 minutes

  Your App URL After Deployment:
    https://foodbridge-production.up.railway.app
    (or your own custom domain if you connect one)


---
Guide generated for: FoodBridge — Flask 3.0.3 + MySQL + Gunicorn 22.0.0
Deployment target:   Railway.app Free Tier ($5/month credit)
Project structure:   Blueprints, Application Factory, SQLAlchemy ORM, Flask-Migrate
