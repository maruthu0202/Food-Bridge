# FoodBridge — Technology Stack

## Project Summary

**FoodBridge** is a full-stack web application built with Python and Flask to connect food donors with NGOs for surplus food redistribution. The application uses an application factory pattern, Blueprint-based routing, a service layer for business logic, and supports both local SQLite (development) and MySQL / Google Cloud SQL (production) databases.

---

## Backend Framework

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.10.x | Primary server-side language |
| **Flask** | 3.0.3 | WSGI web framework (application factory pattern) |
| **Werkzeug** | 3.0.3 | WSGI utilities, password hashing, request handling |
| **Gunicorn** | 22.0.0 | Production WSGI server (for GCP App Engine deployment) |

---

## Database & ORM

| Technology | Version | Purpose |
|------------|---------|---------|
| **SQLAlchemy** | 2.0.32 | Python SQL toolkit and ORM |
| **Flask-SQLAlchemy** | 3.1.1 | Flask integration for SQLAlchemy |
| **Flask-Migrate** | 4.0.7 | Database schema migrations (Alembic) |
| **Alembic** | 1.19.x | Underlying migration engine |
| **SQLite** | Built-in | Development database (zero-config) |
| **MySQL / PyMySQL** | 1.1.1 | Production database driver |
| **Google Cloud SQL** | — | Managed MySQL in production (App Engine) |

---

## Authentication & Security

| Technology | Version | Purpose |
|------------|---------|---------|
| **Flask-Login** | 0.6.3 | User session management, `@login_required` decorator |
| **Flask-WTF / WTForms** | 1.2.1 / 3.1.2 | CSRF protection on all form submissions |
| **cryptography** | 42.0.8 | Dependency for PyMySQL SSL connections |
| **python-dotenv** | 1.0.1 | Load environment variables from `.env` file |

Password storage uses `werkzeug.security.generate_password_hash` with `pbkdf2:sha256` algorithm.

---

## Cloud & Storage

| Technology | Version | Purpose |
|------------|---------|---------|
| **Google Cloud Storage** | 2.17.0 | Production image hosting for food photos |
| **google-auth** | 2.x | Google Cloud service account authentication |
| **Pillow** | 10.4.0 | Image processing and MIME-type validation |
| **Local Upload Folder** | — | Development fallback (stores images in `uploads/`) |

---

## Frontend / UI

| Technology | Version | Purpose |
|------------|---------|---------|
| **Jinja2** | 3.1.6 | Server-side HTML templating engine (built into Flask) |
| **Bootstrap 5** | 5.3.3 | Responsive CSS framework (via CDN) |
| **Bootstrap Icons** | 1.11.3 | Icon set (via CDN) |
| **Google Fonts — Inter** | — | Modern sans-serif typography |
| **Vanilla CSS** | — | Custom glassmorphism dark theme (`app/static/css/main.css`) |
| **Vanilla JavaScript** | — | Flash alert auto-dismiss, Bootstrap tooltips (`app/static/js/main.js`) |

---

## Email Validation

| Technology | Version | Purpose |
|------------|---------|---------|
| **email-validator** | 2.2.0 | RFC-compliant email format validation |
| **dnspython** | 2.x | DNS resolution dependency for email-validator |

---

## Testing

| Technology | Version | Purpose |
|------------|---------|---------|
| **pytest** | 8.3.2 | Test runner and discovery framework |
| **pytest-flask** | 1.3.0 | Flask-specific test fixtures and client |
| **coverage** | 7.6.1 | Code coverage measurement |
| **SQLite in-memory** | — | Isolated test database (reset between test runs) |

Test files are in the `tests/` directory:
- `tests/conftest.py` — Fixtures (app, client, donor_user, ngo_user, admin_user)
- `tests/test_auth.py` — Registration, login, and session tests
- `tests/test_donations.py` — Donation creation and expiry lifecycle tests
- `tests/test_pickups.py` — Full pickup lifecycle and matching algorithm tests
- `tests/test_api.py` — REST API endpoint tests

---

## Project Structure

```
cloud mini/
├── app.py                      # Application entry point
├── requirements.txt            # Python dependencies
├── seed.py                     # Database demo data seeder
├── WORKFLOW.md                 # Application workflow documentation
├── TECH_STACK.md               # Technology stack documentation (this file)
├── .env.example                # Environment variable template
├── food_donation_dev.db        # SQLite dev database (auto-created)
├── uploads/                    # Local file upload storage (dev)
├── tests/                      # Pytest test suite
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_donations.py
│   ├── test_pickups.py
│   └── test_api.py
└── app/
    ├── __init__.py             # Application factory (create_app)
    ├── config.py               # DevelopmentConfig, ProductionConfig, TestingConfig
    ├── extensions.py           # Flask extension instances (db, migrate, login, csrf)
    ├── models/
    │   ├── user.py             # User model (UserRole, Flask-Login mixin)
    │   ├── donation.py         # Donation model (state machine, FoodType, QuantityUnit)
    │   ├── pickup_request.py   # PickupRequest model (state machine)
    │   ├── distribution.py     # Distribution model (impact tracking)
    │   └── audit_log.py        # AuditLog model (immutable event log)
    ├── routes/
    │   ├── main.py             # Public pages (landing, about, dashboard redirect)
    │   ├── auth.py             # Registration, login, logout, profile
    │   ├── donor.py            # Donor CRUD and pickup request management
    │   ├── ngo.py              # NGO discovery, requests, distributions
    │   ├── admin.py            # Admin panel (users, donations, stats)
    │   └── api.py              # REST JSON API endpoints
    ├── services/
    │   ├── donation_service.py # Donation business logic (create, update, expire)
    │   ├── pickup_service.py   # Pickup request lifecycle (accept, reject, complete)
    │   ├── matching_service.py # Weighted scoring algorithm for NGO donation ranking
    │   ├── location_service.py # Haversine distance, bounding box, radius filter
    │   └── storage_service.py  # GCS / local file upload abstraction
    ├── utils/
    │   ├── decorators.py       # @donor_required, @ngo_required, @admin_required
    │   ├── helpers.py          # Jinja2 filters (time_until, format_datetime), get_client_ip
    │   └── validators.py       # Form input validators (email, password, donation, lat/lon)
    ├── static/
    │   ├── css/main.css        # Custom dark glassmorphism theme
    │   └── js/main.js          # Client-side interactivity
    └── templates/
        ├── base.html           # Master layout (navbar, flash messages, footer)
        ├── auth/               # login.html, register.html, profile.html
        ├── donor/              # dashboard.html, create_donation.html, etc.
        ├── ngo/                # dashboard.html, nearby_donations.html, etc.
        ├── admin/              # dashboard.html, users.html, statistics.html, etc.
        ├── main/               # index.html, about.html
        └── errors/             # 400.html, 401.html, 403.html, 404.html, 409.html, 500.html
```

---

## Configuration Environments

| Environment | Database | Debug | CSRF | Cookie Secure |
|-------------|----------|-------|------|---------------|
| `development` | SQLite (local file) | ON | ON | OFF |
| `production` | MySQL / Cloud SQL | OFF | ON | ON |
| `testing` | SQLite in-memory | OFF | OFF | OFF |

The active environment is controlled by the `FLASK_ENV` environment variable (default: `development`).

---

## Running the Application

### Quick Start (Development)

```bash
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate        # Windows
source venv/bin/activate       # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Seed demo data (optional)
python seed.py

# 4. Start the development server
python app.py
# OR
flask run
```

Application runs at: **http://127.0.0.1:5000**

### Run Tests

```bash
python -m pytest -v
```

### Run with Coverage Report

```bash
python -m pytest --cov=app --cov-report=term-missing
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLASK_ENV` | No | `development` | Config profile to load |
| `SECRET_KEY` | Yes (prod) | `change-me-in-production` | Flask session signing key |
| `DATABASE_URL` | No | SQLite local file | Full SQLAlchemy DB URI |
| `GOOGLE_CLOUD_PROJECT` | No | `""` | GCP project ID |
| `GCS_BUCKET_NAME` | No | `""` | GCS bucket for image uploads |
| `DB_USER` | Prod only | `""` | Cloud SQL username |
| `DB_PASS` | Prod only | `""` | Cloud SQL password |
| `DB_NAME` | Prod only | `food_donation_prod` | Production database name |
| `CLOUD_SQL_CONNECTION_NAME` | Prod only | `""` | Cloud SQL Unix socket name |

Copy `.env.example` to `.env` and fill in the values before running.

---

## Production Deployment (Google Cloud App Engine)

1. Set environment variables in `app.yaml` or GCP Secret Manager
2. Configure Cloud SQL instance and set `CLOUD_SQL_CONNECTION_NAME`
3. Create a GCS bucket and set `GCS_BUCKET_NAME`
4. Deploy with: `gcloud app deploy`
5. Gunicorn is used automatically as the production WSGI server
