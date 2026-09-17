"""Authentication routes — register, login, logout, profile."""
import logging
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.utils.decorators import active_required
from app.utils.helpers import get_client_ip
from app.utils.validators import validate_email, validate_password, validate_registration

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        data = request.form.to_dict()
        errors = validate_registration(data)

        # Check unique email
        if not errors and User.query.filter_by(email=data["email"].lower().strip()).first():
            errors.append("An account with this email already exists.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register.html", form_data=data, roles=UserRole.ALL)

        user = User(
            email=data["email"].lower().strip(),
            full_name=data["full_name"].strip(),
            role=data["role"],
            phone=data.get("phone", "").strip() or None,
            org_name=data.get("org_name", "").strip() or None,
        )
        user.set_password(data["password"])
        db.session.add(user)

        log = AuditLog(
            action="user_registered",
            entity_type="User",
            ip_address=get_client_ip(),
            details=f"Role: {data['role']}",
        )
        db.session.add(log)
        db.session.commit()

        # Set user_id on the log now that user has an id
        log.user_id = user.id
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        logger.info("New user registered: %s [%s]", user.email, user.role)
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form_data={}, roles=[UserRole.DONOR, UserRole.NGO])


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            logger.warning("Failed login attempt for email: %s from IP: %s", email, get_client_ip())
            db.session.add(AuditLog(
                action="login_failed",
                ip_address=get_client_ip(),
                details=f"Email: {email}",
            ))
            db.session.commit()
            return render_template("auth/login.html")

        if not user.is_active:
            flash("Your account has been suspended. Please contact support.", "danger")
            return render_template("auth/login.html")

        login_user(user, remember=remember)
        user.last_login_at = datetime.utcnow()
        db.session.add(AuditLog(
            user_id=user.id,
            action="login_success",
            ip_address=get_client_ip(),
        ))
        db.session.commit()

        logger.info("User %s logged in", user.email)
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logger.info("User %s logged out", current_user.email)
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
@active_required
def profile():
    if request.method == "POST":
        data = request.form
        errors = []

        full_name = data.get("full_name", "").strip()
        if not full_name or len(full_name) > 150:
            errors.append("Full name must be between 1 and 150 characters.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/profile.html")

        current_user.full_name = full_name
        current_user.phone = data.get("phone", "").strip() or None
        current_user.address = data.get("address", "").strip() or None
        current_user.org_name = data.get("org_name", "").strip() or None
        current_user.org_description = data.get("org_description", "").strip() or None

        # Update password if provided
        new_password = data.get("new_password", "")
        if new_password:
            ok, msg = validate_password(new_password)
            if not ok:
                flash(msg, "danger")
                return render_template("auth/profile.html")
            if new_password != data.get("confirm_password", ""):
                flash("New passwords do not match.", "danger")
                return render_template("auth/profile.html")
            current_user.set_password(new_password)

        db.session.commit()
        flash("Profile updated successfully.", "success")

    return render_template("auth/profile.html")
