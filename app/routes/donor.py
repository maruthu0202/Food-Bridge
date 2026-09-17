"""Donor routes — donation CRUD and pickup request management."""
import logging
from datetime import datetime

from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required

from app.extensions import db
from app.models.donation import Donation, DonationStatus, FoodType, QuantityUnit
from app.models.pickup_request import PickupRequest, RequestStatus
from app.services.donation_service import DonationService
from app.services.pickup_service import PickupService
from app.services.storage_service import storage_service
from app.utils.decorators import donor_required
from app.utils.validators import validate_donation, validate_lat_lon

logger = logging.getLogger(__name__)
donor_bp = Blueprint("donor", __name__)


# ------------------------------------------------------------------ #
#  Dashboard                                                            #
# ------------------------------------------------------------------ #

@donor_bp.route("/dashboard")
@donor_required
def dashboard():
    donations = (
        Donation.query
        .filter_by(donor_id=current_user.id)
        .order_by(Donation.created_at.desc())
        .limit(5)
        .all()
    )
    active_count = Donation.query.filter(
        Donation.donor_id == current_user.id,
        Donation.status.in_(DonationStatus.ACTIVE),
    ).count()
    completed_count = Donation.query.filter(
        Donation.donor_id == current_user.id,
        Donation.status == DonationStatus.DELIVERED,
    ).count()
    pending_requests = PickupRequest.query.join(Donation).filter(
        Donation.donor_id == current_user.id,
        PickupRequest.status == RequestStatus.PENDING,
    ).count()

    return render_template(
        "donor/dashboard.html",
        recent_donations=donations,
        active_count=active_count,
        completed_count=completed_count,
        pending_requests=pending_requests,
    )


# ------------------------------------------------------------------ #
#  Donation CRUD                                                        #
# ------------------------------------------------------------------ #

@donor_bp.route("/donations")
@donor_required
def my_donations():
    page = request.args.get("page", 1, type=int)
    status_filter = request.args.get("status", "")
    query = Donation.query.filter_by(donor_id=current_user.id)
    if status_filter:
        query = query.filter(Donation.status == status_filter)
    pagination = query.order_by(Donation.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    return render_template(
        "donor/my_donations.html",
        pagination=pagination,
        statuses=vars(DonationStatus),
        status_filter=status_filter,
    )


@donor_bp.route("/donations/create", methods=["GET", "POST"])
@donor_required
def create_donation():
    if request.method == "POST":
        data = request.form.to_dict()
        errors = validate_donation(data)

        lat, lon, coord_err = validate_lat_lon(data.get("latitude"), data.get("longitude"))
        if coord_err:
            errors.append(coord_err)

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "donor/create_donation.html",
                food_types=FoodType.ALL,
                units=QuantityUnit.ALL,
                form_data=data,
            )

        data["latitude"] = lat
        data["longitude"] = lon

        # Parse datetime strings from form
        try:
            data["prepared_at"] = datetime.fromisoformat(data["prepared_at"])
            data["expiry_at"] = datetime.fromisoformat(data["expiry_at"])
        except (ValueError, KeyError):
            flash("Invalid date format.", "danger")
            return render_template(
                "donor/create_donation.html",
                food_types=FoodType.ALL,
                units=QuantityUnit.ALL,
                form_data=data,
            )

        image_file = request.files.get("image")
        try:
            donation = DonationService.create_donation(current_user.id, data, image_file)
            flash("Donation created successfully!", "success")
            return redirect(url_for("donor.donation_detail", donation_id=donation.id))
        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template(
        "donor/create_donation.html",
        food_types=FoodType.ALL,
        units=QuantityUnit.ALL,
        form_data={},
    )


@donor_bp.route("/donations/<int:donation_id>")
@donor_required
def donation_detail(donation_id):
    donation = Donation.query.get_or_404(donation_id)
    if donation.donor_id != current_user.id:
        abort(403)
    image_url = storage_service.get_image_url(donation.image_path)
    pickup_requests = (
        PickupRequest.query
        .filter_by(donation_id=donation_id)
        .order_by(PickupRequest.requested_at.desc())
        .all()
    )
    return render_template(
        "donor/donation_detail.html",
        donation=donation,
        image_url=image_url,
        pickup_requests=pickup_requests,
    )


@donor_bp.route("/donations/<int:donation_id>/edit", methods=["GET", "POST"])
@donor_required
def edit_donation(donation_id):
    donation = Donation.query.get_or_404(donation_id)
    if donation.donor_id != current_user.id:
        abort(403)

    if request.method == "POST":
        data = request.form.to_dict()
        errors = validate_donation(data)
        lat, lon, coord_err = validate_lat_lon(data.get("latitude"), data.get("longitude"))
        if coord_err:
            errors.append(coord_err)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "donor/edit_donation.html",
                donation=donation,
                food_types=FoodType.ALL,
                units=QuantityUnit.ALL,
            )
        data["latitude"] = lat
        data["longitude"] = lon
        try:
            data["prepared_at"] = datetime.fromisoformat(data["prepared_at"])
            data["expiry_at"] = datetime.fromisoformat(data["expiry_at"])
        except (ValueError, KeyError):
            flash("Invalid date format.", "danger")
            return render_template(
                "donor/edit_donation.html",
                donation=donation,
                food_types=FoodType.ALL,
                units=QuantityUnit.ALL,
            )
        image_file = request.files.get("image")
        try:
            DonationService.update_donation(donation, data, image_file)
            flash("Donation updated.", "success")
            return redirect(url_for("donor.donation_detail", donation_id=donation.id))
        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template(
        "donor/edit_donation.html",
        donation=donation,
        food_types=FoodType.ALL,
        units=QuantityUnit.ALL,
    )


@donor_bp.route("/donations/<int:donation_id>/cancel", methods=["POST"])
@donor_required
def cancel_donation(donation_id):
    donation = Donation.query.get_or_404(donation_id)
    if donation.donor_id != current_user.id:
        abort(403)
    try:
        DonationService.cancel_donation(donation, current_user.id)
        flash("Donation cancelled.", "warning")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("donor.my_donations"))


# ------------------------------------------------------------------ #
#  Pickup request management                                            #
# ------------------------------------------------------------------ #

@donor_bp.route("/requests")
@donor_required
def pickup_requests():
    page = request.args.get("page", 1, type=int)
    requests_q = (
        PickupRequest.query.join(Donation)
        .filter(Donation.donor_id == current_user.id)
        .order_by(PickupRequest.requested_at.desc())
        .paginate(page=page, per_page=15, error_out=False)
    )
    return render_template("donor/pickup_requests.html", pagination=requests_q)


@donor_bp.route("/requests/<int:request_id>/accept", methods=["POST"])
@donor_required
def accept_request(request_id):
    req = PickupRequest.query.get_or_404(request_id)
    try:
        PickupService.accept_request(req, current_user.id)
        flash("Pickup request accepted!", "success")
    except (ValueError, PermissionError) as exc:
        flash(str(exc), "danger")
    return redirect(url_for("donor.donation_detail", donation_id=req.donation_id))


@donor_bp.route("/requests/<int:request_id>/reject", methods=["POST"])
@donor_required
def reject_request(request_id):
    req = PickupRequest.query.get_or_404(request_id)
    try:
        PickupService.reject_request(req, current_user.id)
        flash("Request rejected.", "warning")
    except (ValueError, PermissionError) as exc:
        flash(str(exc), "danger")
    return redirect(url_for("donor.donation_detail", donation_id=req.donation_id))


@donor_bp.route("/requests/<int:request_id>/ready", methods=["POST"])
@donor_required
def mark_ready(request_id):
    req = PickupRequest.query.get_or_404(request_id)
    try:
        PickupService.mark_ready(req, current_user.id)
        flash("Food marked as ready for pickup!", "success")
    except (ValueError, PermissionError) as exc:
        flash(str(exc), "danger")
    return redirect(url_for("donor.donation_detail", donation_id=req.donation_id))
