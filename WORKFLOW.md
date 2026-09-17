# FoodBridge — Application Workflow

## Overview

FoodBridge is a three-role web platform that connects **food donors** (restaurants, hotels, bakeries) with **NGOs** to collect surplus food and distribute it to communities in need. An **Admin** role provides full platform oversight.

---

## System Roles

| Role | Description |
|------|-------------|
| **Donor** | Registers surplus food donations with location, expiry, and quantity details |
| **NGO** | Searches nearby available donations and submits pickup requests |
| **Admin** | Manages all users, donations, requests, and platform statistics |

---

## Core Workflows

### 1. User Registration and Authentication

```
User Visits /auth/register
  |
  +-- Selects Role: [DONOR] or [NGO]
  +-- Fills: name, email, password, phone, org name (NGO only)
  +-- Server-side validation (email format, password strength, role check)
  |
  +-- On Success: Redirected to /auth/login
                    |
                 Logs in -- Session created (Flask-Login)
                    |
                 Redirected to /dashboard (role-based)
```

---

### 2. Donor Workflow — Food Donation Lifecycle

```
Donor visits /donor/dashboard
  |
  +-- [Create Donation] /donor/donations/create
  |     +-- Fills: food name, type, quantity, servings
  |     +-- Sets: prepared_at, expiry_at datetime
  |     +-- Sets: pickup address + lat/lon
  |     +-- Optionally uploads food image
  |               |
  |         Donation created --> Status: AVAILABLE
  |
  +-- [View My Donations] /donor/donations
  |     +-- Filter by status (AVAILABLE, REQUESTED, DELIVERED, etc.)
  |
  +-- [Manage Pickup Requests] /donor/requests
        |
        +-- NGO Requests --> Status: PENDING
        |
        +-- Donor Accepts --> Status: ACCEPTED
        |     +-- All other pending requests --> REJECTED
        |
        +-- Donor Marks Ready --> Status: READY_FOR_PICKUP
        |
        +-- NGO Marks Picked Up --> Status: PICKED_UP
              +-- NGO Records Distribution --> Status: DELIVERED
```

---

### 3. NGO Workflow — Food Discovery and Pickup

```
NGO visits /ngo/dashboard
  |
  +-- [Find Available Food] /ngo/donations
  |     +-- Matching Algorithm ranks donations:
  |     |     - Distance Score (50%) -- closer = higher
  |     |     - Expiry Urgency (35%) -- sooner expiry = higher
  |     |     - Quantity Score (15%) -- more servings = higher
  |     +-- Filter by radius (default 25km), food type, sort order
  |
  +-- [View Donation Details] /ngo/donations/<id>
  |     +-- Submits Pickup Request --> Status: PENDING
  |
  +-- [My Requests] /ngo/requests
  |     +-- Track request status from PENDING to COMPLETED
  |
  +-- [Distribution History] /ngo/distributions
        +-- View all completed distributions with people served counts
```

---

### 4. Admin Workflow — Platform Management

```
Admin visits /admin/dashboard
  |
  +-- [Users] /admin/users
  |     +-- Suspend / Activate donor and NGO accounts
  |
  +-- [Donations] /admin/donations
  |     +-- View all donations, cancel active ones
  |
  +-- [Pickup Requests] /admin/requests
  |     +-- Full view of all pending and active requests
  |
  +-- [Distributions] /admin/distributions
  |     +-- Track total impact: quantity, people served
  |
  +-- [Statistics] /admin/statistics
  |     +-- Monthly distribution breakdown
  |     +-- Food type category analysis
  |
  +-- [Expire Donations] POST /admin/expire-donations
        +-- Marks stale AVAILABLE/REQUESTED past-expiry as EXPIRED
```

---

## Donation Status State Machine

```
AVAILABLE
  |
  +---> REQUESTED (NGO submits pickup request)
  |       |
  |       +---> ACCEPTED (Donor approves request)
  |       |       |
  |       |       +---> READY_FOR_PICKUP (Donor marks food ready)
  |       |                 |
  |       |                 +---> PICKED_UP (NGO physically collects)
  |       |                           |
  |       |                           +---> DELIVERED (NGO records distribution)
  |       |
  |       +---> AVAILABLE (if all requests rejected)
  |
  +---> CANCELLED (donor or admin cancels at any active stage)
  +---> EXPIRED (auto-expired when past expiry datetime)
```

---

## Pickup Request State Machine

```
PENDING ---> ACCEPTED ---> READY_FOR_PICKUP ---> PICKED_UP ---> COMPLETED
         \-> REJECTED
PENDING or ACCEPTED ---> CANCELLED
```

---

## REST API Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/api/donations` | List available donations (paginated) | No |
| `GET` | `/api/donations/nearby` | Ranked donations near lat/lng/radius | No |
| `GET` | `/api/donations/<id>` | Single donation detail | No |
| `POST` | `/api/donations/<id>/requests` | NGO submits pickup request | Yes (NGO) |
| `PATCH` | `/api/requests/<id>/status` | Update request status | Yes |
| `GET` | `/api/dashboard/stats` | Platform-wide impact statistics | Yes |

---

## Matching Algorithm

The `DonationMatchingService` scores each available donation for an NGO:

```
score = 0.50 x distance_score
      + 0.35 x expiry_urgency_score
      + 0.15 x quantity_score
```

- **distance_score**: `1 - (distance_km / 50.0)` — capped at 50 km radius
- **expiry_urgency_score**: `1 - (hours_remaining / 48.0)` — urgency within 48 hours window
- **quantity_score**: `min(1.0, servings / 200)` — rewards larger batch donations

Donations outside the NGO's configured radius are excluded from results.

---

## Image Storage Strategy

| Environment | Storage Backend |
|-------------|----------------|
| Development (no GCS_BUCKET_NAME set) | Local `uploads/` folder, served at `/uploads/<path>` |
| Production (GCS_BUCKET_NAME set) | Google Cloud Storage bucket, public CDN URL |

---

## Security Features

- **CSRF Protection** — Flask-WTF CSRFProtect on all POST/PATCH/DELETE forms
- **Password Hashing** — Werkzeug `generate_password_hash` (pbkdf2:sha256)
- **Session Security** — `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE=Lax`
- **Role Decorators** — `@donor_required`, `@ngo_required`, `@admin_required` enforce role-based access
- **Input Validation** — Server-side validators for all form fields and geographic coordinates
- **Audit Logs** — Immutable `AuditLog` records for registration, login, donations, and distributions

---

## Demo Accounts (After Running seed.py)

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@foodbridge.org | Admin@123 |
| Donor | donor@citybakery.com | Donor@123 |
| Donor | manager@metrohotel.com | Donor@123 |
| NGO | ngo@hopeshelter.org | Ngo@123 |
| NGO | contact@foodfirst.org | Ngo@123 |
