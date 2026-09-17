"""PickupService — business logic for pickup request lifecycle."""
import logging

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.donation import Donation, DonationStatus
from app.models.pickup_request import PickupRequest, RequestStatus
from app.models.distribution import Distribution

logger = logging.getLogger(__name__)


class PickupService:

    @staticmethod
    def create_request(ngo_id: int, donation: Donation, notes: str = "") -> PickupRequest:
        """NGO requests pickup of a donation.

        Uses a DB-level check to prevent duplicate active requests.
        """
        if donation.status != DonationStatus.AVAILABLE:
            raise ValueError("This donation is no longer available.")

        # Check for existing active request by this NGO
        existing = PickupRequest.query.filter(
            PickupRequest.donation_id == donation.id,
            PickupRequest.ngo_id == ngo_id,
            PickupRequest.status.in_(RequestStatus.ACTIVE),
        ).first()
        if existing:
            raise ValueError("You already have an active request for this donation.")

        # Check if another NGO has an accepted request (donation is no longer truly available)
        accepted = PickupRequest.query.filter(
            PickupRequest.donation_id == donation.id,
            PickupRequest.status.in_([
                RequestStatus.ACCEPTED,
                RequestStatus.READY_FOR_PICKUP,
                RequestStatus.PICKED_UP,
            ]),
        ).first()
        if accepted:
            raise ValueError("This donation has already been claimed by another NGO.")

        req = PickupRequest(
            donation_id=donation.id,
            ngo_id=ngo_id,
            notes=notes,
            status=RequestStatus.PENDING,
        )
        db.session.add(req)

        # Move donation to REQUESTED state
        donation.transition_to(DonationStatus.REQUESTED)

        log = AuditLog(
            user_id=ngo_id,
            action="pickup_requested",
            entity_type="PickupRequest",
            entity_id=req.id,
            details=f"Donation {donation.id}",
        )
        db.session.add(log)
        db.session.commit()
        logger.info("PickupRequest created by NGO %d for donation %d", ngo_id, donation.id)
        return req

    @staticmethod
    def accept_request(request: PickupRequest, donor_id: int) -> PickupRequest:
        """Donor accepts a pickup request. Rejects all other pending requests."""
        donation = request.donation
        if donation.donor_id != donor_id:
            raise PermissionError("Not your donation.")

        request.transition_to(RequestStatus.ACCEPTED)
        donation.transition_to(DonationStatus.ACCEPTED)

        # Reject all other pending requests for this donation
        others = PickupRequest.query.filter(
            PickupRequest.donation_id == donation.id,
            PickupRequest.id != request.id,
            PickupRequest.status == RequestStatus.PENDING,
        ).all()
        for other in others:
            other.status = RequestStatus.REJECTED

        log = AuditLog(
            user_id=donor_id,
            action="request_accepted",
            entity_type="PickupRequest",
            entity_id=request.id,
        )
        db.session.add(log)
        db.session.commit()
        logger.info("Request %d accepted by donor %d", request.id, donor_id)
        return request

    @staticmethod
    def reject_request(request: PickupRequest, donor_id: int) -> PickupRequest:
        """Donor rejects a pickup request."""
        if request.donation.donor_id != donor_id:
            raise PermissionError("Not your donation.")

        request.transition_to(RequestStatus.REJECTED)

        # If no other pending requests, make donation AVAILABLE again
        other_pending = PickupRequest.query.filter(
            PickupRequest.donation_id == request.donation_id,
            PickupRequest.id != request.id,
            PickupRequest.status == RequestStatus.PENDING,
        ).count()

        if other_pending == 0:
            request.donation.transition_to(DonationStatus.AVAILABLE)

        db.session.commit()
        return request

    @staticmethod
    def mark_ready(request: PickupRequest, donor_id: int) -> PickupRequest:
        """Donor marks food as ready for pickup."""
        if request.donation.donor_id != donor_id:
            raise PermissionError("Not your donation.")
        request.transition_to(RequestStatus.READY_FOR_PICKUP)
        request.donation.transition_to(DonationStatus.READY_FOR_PICKUP)
        db.session.commit()
        return request

    @staticmethod
    def mark_picked_up(request: PickupRequest, ngo_id: int) -> PickupRequest:
        """NGO marks food as picked up."""
        if request.ngo_id != ngo_id:
            raise PermissionError("Not your request.")
        request.transition_to(RequestStatus.PICKED_UP)
        request.donation.transition_to(DonationStatus.PICKED_UP)
        db.session.commit()
        return request

    @staticmethod
    def complete_with_distribution(
        request: PickupRequest,
        ngo_id: int,
        quantity_distributed: float,
        quantity_unit: str,
        people_served: int,
        remarks: str = "",
    ) -> Distribution:
        """NGO marks as delivered and records distribution impact."""
        if request.ngo_id != ngo_id:
            raise PermissionError("Not your request.")
        if request.status != RequestStatus.PICKED_UP:
            raise ValueError("Request must be in PICKED_UP state to complete.")

        request.transition_to(RequestStatus.COMPLETED)
        request.donation.transition_to(DonationStatus.DELIVERED)

        distribution = Distribution(
            pickup_request_id=request.id,
            quantity_distributed=quantity_distributed,
            quantity_unit=quantity_unit,
            people_served=people_served,
            remarks=remarks,
        )
        db.session.add(distribution)

        log = AuditLog(
            user_id=ngo_id,
            action="distribution_recorded",
            entity_type="Distribution",
            details=f"Served {people_served} people",
        )
        db.session.add(log)
        db.session.commit()
        logger.info(
            "Distribution recorded for request %d — %d people served",
            request.id, people_served,
        )
        return distribution

    @staticmethod
    def cancel_request(request: PickupRequest, user_id: int, is_admin: bool = False):
        """NGO or admin cancels a request."""
        if not is_admin and request.ngo_id != user_id:
            raise PermissionError("Not your request.")

        request.transition_to(RequestStatus.CANCELLED)

        # If donation was REQUESTED and this was the only active request, revert to AVAILABLE
        other_active = PickupRequest.query.filter(
            PickupRequest.donation_id == request.donation_id,
            PickupRequest.id != request.id,
            PickupRequest.status.in_(RequestStatus.ACTIVE),
        ).count()

        if other_active == 0 and request.donation.status in [
            DonationStatus.REQUESTED, DonationStatus.ACCEPTED
        ]:
            request.donation.transition_to(DonationStatus.AVAILABLE)

        db.session.commit()
