"""Tests for pickup request lifecycle and matching algorithm."""
from datetime import datetime, timedelta
from app.models.donation import Donation, DonationStatus, FoodType, QuantityUnit
from app.models.pickup_request import RequestStatus
from app.services.donation_service import DonationService
from app.services.pickup_service import PickupService
from app.services.matching_service import DonationMatchingService


def test_pickup_lifecycle(app, donor_user, ngo_user):
    with app.app_context():
        now = datetime.utcnow()
        data = {
            "food_name": "Bakery Bread",
            "food_type": FoodType.BAKED,
            "quantity": 20.0,
            "quantity_unit": QuantityUnit.PIECES,
            "servings": 20,
            "prepared_at": now - timedelta(hours=1),
            "expiry_at": now + timedelta(hours=24),
            "pickup_address": "456 Market St",
            "latitude": 37.7749,
            "longitude": -122.4194,
        }
        donation = DonationService.create_donation(donor_user.id, data)

        # NGO creates request
        req = PickupService.create_request(ngo_user.id, donation, "Need bread for shelter")
        assert req.status == RequestStatus.PENDING
        assert donation.status == DonationStatus.REQUESTED

        # Donor accepts request
        PickupService.accept_request(req, donor_user.id)
        assert req.status == RequestStatus.ACCEPTED
        assert donation.status == DonationStatus.ACCEPTED

        # Donor marks ready
        PickupService.mark_ready(req, donor_user.id)
        assert req.status == RequestStatus.READY_FOR_PICKUP
        assert donation.status == DonationStatus.READY_FOR_PICKUP

        # NGO marks picked up
        PickupService.mark_picked_up(req, ngo_user.id)
        assert req.status == RequestStatus.PICKED_UP

        # NGO completes distribution
        dist = PickupService.complete_with_distribution(
            req, ngo_user.id, 20.0, QuantityUnit.PIECES, 20, "Distributed all pieces"
        )
        assert dist.id is not None
        assert dist.people_served == 20
        assert donation.status == DonationStatus.DELIVERED


def test_matching_ranking(app, donor_user):
    with app.app_context():
        now = datetime.utcnow()
        d1 = DonationService.create_donation(donor_user.id, {
            "food_name": "Close Food",
            "food_type": FoodType.COOKED,
            "quantity": 10.0,
            "quantity_unit": QuantityUnit.KG,
            "servings": 30,
            "prepared_at": now,
            "expiry_at": now + timedelta(hours=6),
            "pickup_address": "Near",
            "latitude": 37.7749,
            "longitude": -122.4194,
        })
        d2 = DonationService.create_donation(donor_user.id, {
            "food_name": "Far Food",
            "food_type": FoodType.COOKED,
            "quantity": 10.0,
            "quantity_unit": QuantityUnit.KG,
            "servings": 30,
            "prepared_at": now,
            "expiry_at": now + timedelta(hours=48),
            "pickup_address": "Far",
            "latitude": 37.9000,
            "longitude": -122.5000,
        })

        available = [d1, d2]
        ranked = DonationMatchingService.rank_donations(available, 37.7749, -122.4194, radius_km=50)
        assert len(ranked) == 2
        # d1 should have higher score due to closer distance & urgent expiry
        assert ranked[0][2].id == d1.id
