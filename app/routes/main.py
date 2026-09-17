"""Main/public routes — landing, about, dashboard redirect."""
from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user

from app.models.donation import Donation, DonationStatus
from app.models.distribution import Distribution
from app.models.user import UserRole
from app.extensions import db
from sqlalchemy import func

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    # Public stats for landing page
    total_donations = Donation.query.filter(
        Donation.status == DonationStatus.DELIVERED
    ).count()
    total_people = db.session.query(func.sum(Distribution.people_served)).scalar() or 0

    return render_template(
        "main/index.html",
        total_donations=total_donations,
        total_people=total_people,
    )


@main_bp.route("/about")
def about():
    return render_template("main/about.html")


@main_bp.route("/dashboard")
def dashboard():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.is_donor:
        return redirect(url_for("donor.dashboard"))
    if current_user.is_ngo:
        return redirect(url_for("ngo.dashboard"))
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("main.index"))


@main_bp.route("/uploads/<path:filename>")
def serve_upload(filename):
    """Serve locally stored upload files (dev only)."""
    import os
    from flask import current_app, send_from_directory
    upload_folder = current_app.config["LOCAL_UPLOAD_FOLDER"]
    return send_from_directory(upload_folder, filename)
