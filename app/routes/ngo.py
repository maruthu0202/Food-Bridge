"""NGO routes — discover donations, request pickups, track distributions."""
import logging

from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user

from app.extensions import db
from app.models.donation import Donation, DonationStatus, FoodType
from app.models.distribution import Distribution
from app.models.pickup_request import PickupRequest, RequestStatus
from app.services.donation_service import DonationService
from app.services.matching_service import DonationMatchingService
from app.services.pickup_service import PickupService
from app.services.storage_service import storage_service
from app.utils.decorators import ngo_required

logger = logging.getLogger(__name__)
ngo_bp = Blueprint("ngo", __name__)


@ngo_bp.route("/dashboard")
@ngo_required
def dashboard():
    active_requests = PickupRequest.query.filter(
        PickupRequest.ngo_id == current_user.id,
        PickupRequest.status.in_(RequestStatus.ACTIVE),
    ).count()
    completed = PickupRequest.query.filter(
        PickupRequest.ngo_id == current_user.id,
        PickupRequest.status == RequestStatus.COMPLETED,
    ).count()

    from sqlalchemy import func
    people_served = (
        db.session.query(func.sum(Distribution.people_served))
        .join(PickupRequest)
        .filter(PickupRequest.ngo_id == current_user.id)
        .scalar() or 0
    )

    recent_requests = (
        PickupRequest.query
        .filter_by(ngo_id=current_user.id)
        .order_by(PickupRequest.requested_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "ngo/dashboard.html",
        active_requests=active_requests,
        completed=completed,
        people_served=people_served,
        recent_requests=recent_requests,
    )


@ngo_bp.route("/donations")
@ngo_required
def nearby_donations():
    """Show available donations, sorted by matching score."""
    radius_km = request.args.get("radius", 25, type=float)
    food_type = request.args.get("food_type", "")
    sort_by = request.args.get("sort", "score")  # score | expiry | distance

    available = DonationService.get_available_donations(food_type=food_type or None)

    # Run matching algorithm
    ranked = DonationMatchingService.rank_donations(
        donations=available,
        ngo_lat=current_user.latitude,
        ngo_lon=current_user.longitude,
        radius_km=radius_km,
    )

    # Alternative sort
    if sort_by == "expiry":
        ranked.sort(key=lambda x: x[2].expiry_at)
    elif sort_by == "distance":
        ranked.sort(key=lambda x: x[1])

    # Attach image URLs
    enriched = [
        {
            "score": score,
            "distance": dist,
            "donation": d,
            "image_url": storage_service.get_image_url(d.image_path),
        }
        for score, dist, d in ranked
    ]

    # All donations without coord filter for map
    map_donations = [
        {
            "id": d.id,
            "lat": d.latitude,
            "lon": d.longitude,
            "name": d.food_name,
            "address": d.pickup_address,
            "expiry": d.expiry_at.isoformat() if d.expiry_at else None,
        }
        for d in available
        if d.latitude and d.longitude
    ]

    return render_template(
        "ngo/nearby_donations.html",
        enriched=enriched,
        food_types=FoodType.ALL,
        radius_km=radius_km,
        food_type=food_type,
        sort_by=sort_by,
        map_donations=map_donations,
        ngo_lat=current_user.latitude,
        ngo_lon=current_user.longitude,
    )


@ngo_bp.route("/donations/<int:donation_id>")
@ngo_required
def donation_detail(donation_id):
    donation = Donation.query.get_or_404(donation_id)
    if donation.status == DonationStatus.EXPIRED:
        flash("This donation has expired.", "warning")

    image_url = storage_service.get_image_url(donation.image_path)

    # Check if current NGO already has a request
    existing_request = PickupRequest.query.filter_by(
        donation_id=donation_id,
        ngo_id=current_user.id,
    ).filter(PickupRequest.status.in_(RequestStatus.ACTIVE)).first()

    from app.services.location_service import LocationService
    distance = None
    if current_user.latitude and donation.latitude:
        distance = LocationService.distance_between(
            (current_user.latitude, current_user.longitude),
            (donation.latitude, donation.longitude),
        )

    return render_template(
        "ngo/donation_detail.html",
        donation=donation,
        image_url=image_url,
        existing_request=existing_request,
        distance=distance,
    )


@ngo_bp.route("/donations/<int:donation_id>/request", methods=["POST"])
@ngo_required
def request_pickup(donation_id):
    donation = Donation.query.get_or_404(donation_id)
    notes = request.form.get("notes", "").strip()
    try:
        PickupService.create_request(current_user.id, donation, notes)
        flash("Pickup request submitted!", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("ngo.donation_detail", donation_id=donation_id))


@ngo_bp.route("/requests")
@ngo_required
def my_requests():
    page = request.args.get("page", 1, type=int)
    status_filter = request.args.get("status", "")
    query = PickupRequest.query.filter_by(ngo_id=current_user.id)
    if status_filter:
        query = query.filter(PickupRequest.status == status_filter)
    pagination = query.order_by(PickupRequest.requested_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    return render_template(
        "ngo/my_requests.html",
        pagination=pagination,
        status_filter=status_filter,
    )


@ngo_bp.route("/requests/<int:request_id>/pickup", methods=["POST"])
@ngo_required
def mark_picked_up(request_id):
    req = PickupRequest.query.get_or_404(request_id)
    try:
        PickupService.mark_picked_up(req, current_user.id)
        flash("Marked as picked up! Please record the distribution.", "success")
        return redirect(url_for("ngo.record_distribution", request_id=request_id))
    except (ValueError, PermissionError) as exc:
        flash(str(exc), "danger")
    return redirect(url_for("ngo.my_requests"))


@ngo_bp.route("/requests/<int:request_id>/distribute", methods=["GET", "POST"])
@ngo_required
def record_distribution(request_id):
    req = PickupRequest.query.get_or_404(request_id)
    if req.ngo_id != current_user.id:
        abort(403)

    if request.method == "POST":
        try:
            qty = float(request.form.get("quantity_distributed", 0))
            people = int(request.form.get("people_served", 0))
            unit = request.form.get("quantity_unit", "")
            remarks = request.form.get("remarks", "")

            if qty <= 0 or people <= 0:
                flash("Quantity and people served must be positive.", "danger")
                return render_template("ngo/record_distribution.html", req=req)

            PickupService.complete_with_distribution(
                req, current_user.id, qty, unit, people, remarks
            )
            flash(f"Distribution recorded! {people} people served.", "success")
            return redirect(url_for("ngo.distribution_history"))
        except (ValueError, PermissionError) as exc:
            flash(str(exc), "danger")

    from app.models.donation import QuantityUnit
    return render_template(
        "ngo/record_distribution.html",
        req=req,
        units=QuantityUnit.ALL,
    )


@ngo_bp.route("/distributions")
@ngo_required
def distribution_history():
    distributions = (
        Distribution.query
        .join(PickupRequest)
        .filter(PickupRequest.ngo_id == current_user.id)
        .order_by(Distribution.delivered_at.desc())
        .all()
    )
    total_people = sum(d.people_served for d in distributions)
    return render_template(
        "ngo/distribution_history.html",
        distributions=distributions,
        total_people=total_people,
    )


@ngo_bp.route("/requests/<int:request_id>/cancel", methods=["POST"])
@ngo_required
def cancel_request(request_id):
    req = PickupRequest.query.get_or_404(request_id)
    try:
        PickupService.cancel_request(req, current_user.id)
        flash("Request cancelled.", "warning")
    except (ValueError, PermissionError) as exc:
        flash(str(exc), "danger")
    return redirect(url_for("ngo.my_requests"))
