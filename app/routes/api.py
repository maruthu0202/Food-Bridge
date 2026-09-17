"""REST-style JSON API endpoints."""
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models.donation import Donation, DonationStatus
from app.models.distribution import Distribution
from app.models.pickup_request import PickupRequest
from app.services.donation_service import DonationService
from app.services.location_service import LocationService
from app.services.matching_service import DonationMatchingService
from sqlalchemy import func

logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__)


def _require_auth():
    if not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    return None


# ------------------------------------------------------------------ #
#  Donations                                                            #
# ------------------------------------------------------------------ #

@api_bp.route("/donations", methods=["GET"])
def list_donations():
    status = request.args.get("status", DonationStatus.AVAILABLE)
    food_type = request.args.get("food_type")
    page = request.args.get("page", 1, type=int)

    query = Donation.query.filter_by(status=status)
    if food_type:
        query = query.filter(Donation.food_type == food_type)

    pagination = query.order_by(Donation.expiry_at.asc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return jsonify({
        "donations": [_donation_to_dict(d) for d in pagination.items],
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": page,
    })


@api_bp.route("/donations/nearby", methods=["GET"])
def nearby_donations():
    try:
        lat = float(request.args["lat"])
        lng = float(request.args["lng"])
        radius = float(request.args.get("radius", 25))
    except (KeyError, ValueError):
        return jsonify({"error": "lat, lng required and must be numbers"}), 400

    available = DonationService.get_available_donations()
    ranked = DonationMatchingService.rank_donations(available, lat, lng, radius_km=radius)

    return jsonify({
        "donations": [
            {**_donation_to_dict(d), "distance_km": round(dist, 2), "score": score}
            for score, dist, d in ranked
        ]
    })


@api_bp.route("/donations/<int:donation_id>", methods=["GET"])
def get_donation(donation_id):
    donation = Donation.query.get_or_404(donation_id)
    return jsonify(_donation_to_dict(donation))


@api_bp.route("/donations/<int:donation_id>/requests", methods=["POST"])
@login_required
def create_request(donation_id):
    err = _require_auth()
    if err:
        return err
    if not current_user.is_ngo:
        return jsonify({"error": "Only NGOs can request pickups"}), 403

    donation = Donation.query.get_or_404(donation_id)
    notes = request.get_json(silent=True, force=True) or {}
    notes = notes.get("notes", "")

    from app.services.pickup_service import PickupService
    try:
        req = PickupService.create_request(current_user.id, donation, notes)
        return jsonify({"message": "Request created", "request_id": req.id}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409


@api_bp.route("/requests/<int:request_id>/status", methods=["PATCH"])
@login_required
def update_request_status(request_id):
    err = _require_auth()
    if err:
        return err

    req = PickupRequest.query.get_or_404(request_id)
    body = request.get_json(silent=True, force=True) or {}
    new_status = body.get("status", "")

    from app.services.pickup_service import PickupService
    try:
        if new_status == "ACCEPTED" and current_user.is_donor:
            PickupService.accept_request(req, current_user.id)
        elif new_status == "REJECTED" and current_user.is_donor:
            PickupService.reject_request(req, current_user.id)
        elif new_status == "PICKED_UP" and current_user.is_ngo:
            PickupService.mark_picked_up(req, current_user.id)
        else:
            return jsonify({"error": "Invalid status transition for your role"}), 400
        return jsonify({"message": f"Status updated to {new_status}"})
    except (ValueError, PermissionError) as exc:
        return jsonify({"error": str(exc)}), 400


# ------------------------------------------------------------------ #
#  Dashboard stats                                                      #
# ------------------------------------------------------------------ #

@api_bp.route("/dashboard/stats", methods=["GET"])
@login_required
def dashboard_stats():
    err = _require_auth()
    if err:
        return err

    total_people = db.session.query(func.sum(Distribution.people_served)).scalar() or 0
    total_qty = db.session.query(func.sum(Distribution.quantity_distributed)).scalar() or 0.0
    total_delivered = Donation.query.filter_by(status=DonationStatus.DELIVERED).count()
    active = Donation.query.filter(Donation.status.in_(DonationStatus.ACTIVE)).count()

    return jsonify({
        "total_people_served": total_people,
        "total_quantity_distributed": round(float(total_qty), 2),
        "total_delivered_donations": total_delivered,
        "active_donations": active,
    })


# ------------------------------------------------------------------ #
#  Helpers                                                              #
# ------------------------------------------------------------------ #

def _donation_to_dict(d: Donation) -> dict:
    return {
        "id": d.id,
        "food_name": d.food_name,
        "food_type": d.food_type,
        "quantity": d.quantity,
        "quantity_unit": d.quantity_unit,
        "servings": d.servings,
        "status": d.status,
        "pickup_address": d.pickup_address,
        "latitude": d.latitude,
        "longitude": d.longitude,
        "expiry_at": d.expiry_at.isoformat() if d.expiry_at else None,
        "prepared_at": d.prepared_at.isoformat() if d.prepared_at else None,
        "hours_until_expiry": round(d.hours_until_expiry, 1),
        "donor_id": d.donor_id,
    }
