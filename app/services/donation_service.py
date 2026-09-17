"""DonationService — business logic for donation lifecycle."""
import logging
from datetime import datetime
from typing import Optional

from flask import current_app

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.donation import Donation, DonationStatus
from app.models.pickup_request import PickupRequest, RequestStatus
from app.services.storage_service import storage_service, StorageError

logger = logging.getLogger(__name__)


class DonationService:

    @staticmethod
    def create_donation(donor_id: int, data: dict, image_file=None) -> Donation:
        """Create a new donation, optionally uploading an image."""
        image_path = None
        if image_file and image_file.filename:
            try:
                image_path = storage_service.upload_food_image(image_file)
            except StorageError as exc:
                raise ValueError(str(exc)) from exc

        donation = Donation(
            donor_id=donor_id,
            food_name=data["food_name"],
            food_type=data["food_type"],
            description=data.get("description", ""),
            quantity=float(data["quantity"]),
            quantity_unit=data["quantity_unit"],
            servings=int(data["servings"]),
            prepared_at=data["prepared_at"],
            expiry_at=data["expiry_at"],
            pickup_address=data["pickup_address"],
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            image_path=image_path,
            status=DonationStatus.AVAILABLE,
        )
        db.session.add(donation)

        log = AuditLog(
            user_id=donor_id,
            action="donation_created",
            entity_type="Donation",
            details=f"Food: {data['food_name']}",
        )
        db.session.add(log)
        db.session.commit()
        logger.info("Donation %d created by donor %d", donation.id, donor_id)
        return donation

    @staticmethod
    def update_donation(donation: Donation, data: dict, image_file=None) -> Donation:
        """Update mutable fields. Cannot update once past AVAILABLE."""
        if donation.status not in [DonationStatus.AVAILABLE, DonationStatus.REQUESTED]:
            raise ValueError("Cannot edit donation that is already accepted or beyond.")

        if image_file and image_file.filename:
            # Delete old image
            storage_service.delete_image(donation.image_path)
            try:
                donation.image_path = storage_service.upload_food_image(image_file)
            except StorageError as exc:
                raise ValueError(str(exc)) from exc

        donation.food_name = data.get("food_name", donation.food_name)
        donation.food_type = data.get("food_type", donation.food_type)
        donation.description = data.get("description", donation.description)
        donation.quantity = float(data.get("quantity", donation.quantity))
        donation.quantity_unit = data.get("quantity_unit", donation.quantity_unit)
        donation.servings = int(data.get("servings", donation.servings))
        donation.prepared_at = data.get("prepared_at", donation.prepared_at)
        donation.expiry_at = data.get("expiry_at", donation.expiry_at)
        donation.pickup_address = data.get("pickup_address", donation.pickup_address)
        donation.latitude = data.get("latitude", donation.latitude)
        donation.longitude = data.get("longitude", donation.longitude)
        donation.updated_at = datetime.utcnow()

        db.session.commit()
        return donation

    @staticmethod
    def cancel_donation(donation: Donation, user_id: int):
        """Cancel a donation, rejecting any pending requests."""
        donation.transition_to(DonationStatus.CANCELLED)

        # Cancel all pending/accepted pickup requests
        for req in donation.pickup_requests:
            if req.status in RequestStatus.ACTIVE:
                req.status = RequestStatus.CANCELLED

        log = AuditLog(
            user_id=user_id,
            action="donation_cancelled",
            entity_type="Donation",
            entity_id=donation.id,
        )
        db.session.add(log)
        db.session.commit()
        logger.info("Donation %d cancelled by user %d", donation.id, user_id)

    @staticmethod
    def expire_stale_donations():
        """Mark past-expiry AVAILABLE/REQUESTED donations as EXPIRED (run via cron/admin action)."""
        now = datetime.utcnow()
        stale = Donation.query.filter(
            Donation.expiry_at < now,
            Donation.status.in_([DonationStatus.AVAILABLE, DonationStatus.REQUESTED]),
        ).all()
        for d in stale:
            d.status = DonationStatus.EXPIRED
        if stale:
            db.session.commit()
            logger.info("Expired %d donations", len(stale))
        return len(stale)

    @staticmethod
    def get_available_donations(food_type: Optional[str] = None):
        """Return non-expired available donations."""
        query = Donation.query.filter(
            Donation.status == DonationStatus.AVAILABLE,
            Donation.expiry_at > datetime.utcnow(),
        )
        if food_type:
            query = query.filter(Donation.food_type == food_type)
        return query.order_by(Donation.expiry_at.asc()).all()

    @staticmethod
    def get_image_url(donation: Donation) -> Optional[str]:
        return storage_service.get_image_url(donation.image_path)
