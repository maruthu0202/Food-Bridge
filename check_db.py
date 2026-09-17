"""
============================================================
  FoodBridge - Database & Table Health Check
  File: check_db.py
  Run:  python check_db.py
============================================================
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.donation import Donation, DonationStatus, FoodType
from app.models.pickup_request import PickupRequest, RequestStatus
from app.models.distribution import Distribution
from app.models.audit_log import AuditLog


def divider(char="-", width=60):
    print(char * width)


def section(title):
    print()
    divider("=")
    print(f"  {title}")
    divider("=")


def check_database(app):
    """Check database file / connection details."""
    section("1. DATABASE CONNECTION")

    db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    print(f"  URI      : {db_uri}")

    # SQLite file check
    if db_uri.startswith("sqlite:///"):
        db_path = db_uri.replace("sqlite:///", "")
        if os.path.exists(db_path):
            size_kb = os.path.getsize(db_path) / 1024
            print(f"  File     : {db_path}")
            print(f"  Size     : {size_kb:.2f} KB")
            print(f"  Status   : EXISTS")
        else:
            print(f"  File     : {db_path}")
            print(f"  Status   : NOT FOUND")
    else:
        print(f"  Type     : Remote DB ({db_uri.split('+')[0].upper()})")

    # Connection test
    try:
        conn = db.engine.connect()
        conn.close()
        print(f"  Connect  : SUCCESS")
    except Exception as e:
        print(f"  Connect  : FAILED — {e}")
        return False

    return True


def check_tables(app):
    """Check all tables exist and return row counts."""
    section("2. TABLE EXISTENCE & ROW COUNTS")

    tables = {
        "users"           : User,
        "donations"       : Donation,
        "pickup_requests" : PickupRequest,
        "distributions"   : Distribution,
        "audit_logs"      : AuditLog,
    }

    all_ok = True
    print(f"  {'TABLE':<25} {'ROWS':>6}   STATUS")
    divider()

    for table_name, model in tables.items():
        try:
            count = db.session.query(model).count()
            print(f"  {table_name:<25} {count:>6}   OK")
        except Exception as e:
            print(f"  {table_name:<25} {'ERR':>6}   FAILED — {e}")
            all_ok = False

    return all_ok


def check_users():
    """Detailed user records breakdown."""
    section("3. USERS TABLE — DETAIL")

    total  = User.query.count()
    donors = User.query.filter_by(role=UserRole.DONOR).count()
    ngos   = User.query.filter_by(role=UserRole.NGO).count()
    admins = User.query.filter_by(role=UserRole.ADMIN).count()
    active = User.query.filter_by(is_active=True).count()

    print(f"  Total Users   : {total}")
    print(f"  Donors        : {donors}")
    print(f"  NGOs          : {ngos}")
    print(f"  Admins        : {admins}")
    print(f"  Active        : {active}")
    print()

    users = User.query.all()
    if users:
        print(f"  {'ID':<5} {'ROLE':<8} {'EMAIL':<35} {'ACTIVE'}")
        divider()
        for u in users:
            print(f"  {u.id:<5} {u.role:<8} {u.email:<35} {u.is_active}")
    else:
        print("  No users found in database.")


def check_donations():
    """Detailed donations breakdown by status."""
    section("4. DONATIONS TABLE — DETAIL")

    total = Donation.query.count()
    print(f"  Total Donations : {total}")
    print()

    statuses = [
        DonationStatus.AVAILABLE,
        DonationStatus.REQUESTED,
        DonationStatus.ACCEPTED,
        DonationStatus.READY_FOR_PICKUP,
        DonationStatus.PICKED_UP,
        DonationStatus.DELIVERED,
        DonationStatus.CANCELLED,
        DonationStatus.EXPIRED,
    ]

    print(f"  {'STATUS':<22} {'COUNT':>6}")
    divider()
    for s in statuses:
        c = Donation.query.filter_by(status=s).count()
        print(f"  {s:<22} {c:>6}")

    print()
    donations = Donation.query.all()
    if donations:
        print(f"  {'ID':<5} {'FOOD NAME':<30} {'STATUS':<20} {'EXPIRY'}")
        divider()
        for d in donations:
            expiry = d.expiry_at.strftime("%Y-%m-%d %H:%M") if d.expiry_at else "N/A"
            print(f"  {d.id:<5} {d.food_name[:28]:<30} {d.status:<20} {expiry}")
    else:
        print("  No donations found.")


def check_pickup_requests():
    """Pickup request records."""
    section("5. PICKUP REQUESTS TABLE — DETAIL")

    total = PickupRequest.query.count()
    print(f"  Total Requests : {total}")
    print()

    statuses = [
        RequestStatus.PENDING,
        RequestStatus.ACCEPTED,
        RequestStatus.READY_FOR_PICKUP,
        RequestStatus.PICKED_UP,
        RequestStatus.COMPLETED,
        RequestStatus.REJECTED,
        RequestStatus.CANCELLED,
    ]

    print(f"  {'STATUS':<22} {'COUNT':>6}")
    divider()
    for s in statuses:
        c = PickupRequest.query.filter_by(status=s).count()
        print(f"  {s:<22} {c:>6}")

    print()
    reqs = PickupRequest.query.all()
    if reqs:
        print(f"  {'ID':<5} {'DONATION ID':<12} {'NGO ID':<8} {'STATUS':<20} {'REQUESTED AT'}")
        divider()
        for r in reqs:
            req_at = r.requested_at.strftime("%Y-%m-%d %H:%M") if r.requested_at else "N/A"
            print(f"  {r.id:<5} {r.donation_id:<12} {r.ngo_id:<8} {r.status:<20} {req_at}")
    else:
        print("  No pickup requests found.")


def check_distributions():
    """Distribution records."""
    section("6. DISTRIBUTIONS TABLE — DETAIL")

    total        = Distribution.query.count()
    total_people = sum(d.people_served for d in Distribution.query.all())
    print(f"  Total Distributions : {total}")
    print(f"  Total People Served : {total_people}")
    print()

    dists = Distribution.query.all()
    if dists:
        print(f"  {'ID':<5} {'REQ ID':<8} {'QTY':<10} {'UNIT':<10} {'PEOPLE':<8} {'DELIVERED AT'}")
        divider()
        for d in dists:
            del_at = d.delivered_at.strftime("%Y-%m-%d %H:%M") if d.delivered_at else "N/A"
            print(f"  {d.id:<5} {d.pickup_request_id:<8} {d.quantity_distributed:<10} {d.quantity_unit:<10} {d.people_served:<8} {del_at}")
    else:
        print("  No distribution records found.")


def check_audit_logs():
    """Audit log records."""
    section("7. AUDIT LOGS TABLE — DETAIL")

    total = AuditLog.query.count()
    print(f"  Total Audit Logs : {total}")
    print()

    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
    if logs:
        print(f"  {'ID':<5} {'USER ID':<9} {'ACTION':<30} {'CREATED AT'}")
        divider()
        for log in logs:
            created = log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "N/A"
            user_id = str(log.user_id) if log.user_id else "N/A"
            print(f"  {log.id:<5} {user_id:<9} {log.action:<30} {created}")
    else:
        print("  No audit logs found.")


def summary(db_ok, tables_ok):
    """Print final summary."""
    section("SUMMARY — FINAL RESULT")
    print(f"  Database Connection  : {'PASS' if db_ok     else 'FAIL'}")
    print(f"  All Tables Present   : {'PASS' if tables_ok else 'FAIL'}")
    print()

    if db_ok and tables_ok:
        print("  DATABASE IS HEALTHY AND ALL TABLES ARE WORKING!")
    else:
        print("  ISSUES DETECTED — Please check the errors above.")

    print()
    divider("=")
    print(f"  Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    divider("=")
    print()


# ============================================================
#  MAIN
# ============================================================
if __name__ == "__main__":
    print()
    divider("=")
    print("  FOODBRIDGE — DATABASE & TABLE HEALTH CHECK")
    divider("=")

    app = create_app()

    with app.app_context():
        db_ok     = check_database(app)
        tables_ok = check_tables(app)

        if db_ok:
            check_users()
            check_donations()
            check_pickup_requests()
            check_distributions()
            check_audit_logs()

        summary(db_ok, tables_ok)
