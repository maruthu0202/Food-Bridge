"""Admin routes — full platform management dashboard."""
import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import func

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.distribution import Distribution
from app.models.donation import Donation, DonationStatus
from app.models.pickup_request import PickupRequest, RequestStatus
from app.models.user import User, UserRole
from app.utils.decorators import admin_required

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    stats = {
        "total_users": User.query.count(),
        "total_donors": User.query.filter_by(role=UserRole.DONOR).count(),
        "total_ngos": User.query.filter_by(role=UserRole.NGO).count(),
        "active_donations": Donation.query.filter(
            Donation.status.in_(DonationStatus.ACTIVE)
        ).count(),
        "total_donations": Donation.query.count(),
        "delivered_donations": Donation.query.filter_by(
            status=DonationStatus.DELIVERED
        ).count(),
        "pending_requests": PickupRequest.query.filter_by(
            status=RequestStatus.PENDING
        ).count(),
        "completed_requests": PickupRequest.query.filter_by(
            status=RequestStatus.COMPLETED
        ).count(),
        "total_people_served": db.session.query(
            func.sum(Distribution.people_served)
        ).scalar() or 0,
        "total_quantity_distributed": db.session.query(
            func.sum(Distribution.quantity_distributed)
        ).scalar() or 0.0,
    }
    recent_donations = (
        Donation.query.order_by(Donation.created_at.desc()).limit(5).all()
    )
    recent_logs = (
        AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
    )
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_donations=recent_donations,
        recent_logs=recent_logs,
    )


# ------------------------------------------------------------------ #
#  Users                                                                #
# ------------------------------------------------------------------ #

@admin_bp.route("/users")
@admin_required
def users():
    page = request.args.get("page", 1, type=int)
    role_filter = request.args.get("role", "")
    search = request.args.get("q", "")

    query = User.query
    if role_filter:
        query = query.filter(User.role == role_filter)
    if search:
        query = query.filter(User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%"))

    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template(
        "admin/users.html",
        pagination=pagination,
        role_filter=role_filter,
        search=search,
        roles=UserRole.ALL,
    )


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@admin_required
def toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash("Cannot suspend an admin account.", "danger")
        return redirect(url_for("admin.users"))
    user.is_active = not user.is_active
    db.session.commit()
    state = "activated" if user.is_active else "suspended"
    flash(f"User {user.email} has been {state}.", "success")
    logger.info("Admin toggled user %s active=%s", user.email, user.is_active)
    return redirect(url_for("admin.users"))


# ------------------------------------------------------------------ #
#  Donations                                                            #
# ------------------------------------------------------------------ #

@admin_bp.route("/donations")
@admin_required
def donations():
    page = request.args.get("page", 1, type=int)
    status_filter = request.args.get("status", "")
    query = Donation.query
    if status_filter:
        query = query.filter(Donation.status == status_filter)
    pagination = query.order_by(Donation.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template(
        "admin/donations.html",
        pagination=pagination,
        status_filter=status_filter,
        all_statuses=vars(DonationStatus),
    )


@admin_bp.route("/donations/<int:donation_id>/cancel", methods=["POST"])
@admin_required
def admin_cancel_donation(donation_id):
    from app.services.donation_service import DonationService
    donation = Donation.query.get_or_404(donation_id)
    try:
        DonationService.cancel_donation(donation, current_user_id=None)
        flash("Donation cancelled by admin.", "warning")
    except Exception as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.donations"))


# ------------------------------------------------------------------ #
#  Pickup Requests                                                      #
# ------------------------------------------------------------------ #

@admin_bp.route("/requests")
@admin_required
def pickup_requests():
    page = request.args.get("page", 1, type=int)
    status_filter = request.args.get("status", "")
    query = PickupRequest.query
    if status_filter:
        query = query.filter(PickupRequest.status == status_filter)
    pagination = query.order_by(PickupRequest.requested_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template(
        "admin/requests.html",
        pagination=pagination,
        status_filter=status_filter,
    )


# ------------------------------------------------------------------ #
#  Distributions / Statistics                                           #
# ------------------------------------------------------------------ #

@admin_bp.route("/distributions")
@admin_required
def distributions():
    page = request.args.get("page", 1, type=int)
    pagination = (
        Distribution.query
        .order_by(Distribution.delivered_at.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )
    return render_template("admin/distributions.html", pagination=pagination)


@admin_bp.route("/statistics")
@admin_required
def statistics():
    """Aggregate statistics for platform impact."""
    from sqlalchemy import extract
    from datetime import datetime

    # Monthly distributions
    monthly = (
        db.session.query(
            extract("year", Distribution.delivered_at).label("year"),
            extract("month", Distribution.delivered_at).label("month"),
            func.sum(Distribution.people_served).label("people"),
            func.sum(Distribution.quantity_distributed).label("quantity"),
            func.count(Distribution.id).label("count"),
        )
        .group_by("year", "month")
        .order_by("year", "month")
        .all()
    )

    # Food type breakdown
    food_type_stats = (
        db.session.query(
            Donation.food_type,
            func.count(Donation.id).label("count"),
        )
        .filter(Donation.status == DonationStatus.DELIVERED)
        .group_by(Donation.food_type)
        .all()
    )

    return render_template(
        "admin/statistics.html",
        monthly=monthly,
        food_type_stats=food_type_stats,
    )


@admin_bp.route("/expire-donations", methods=["POST"])
@admin_required
def run_expire():
    from app.services.donation_service import DonationService
    count = DonationService.expire_stale_donations()
    flash(f"Marked {count} donations as expired.", "info")
    return redirect(url_for("admin.donations"))
