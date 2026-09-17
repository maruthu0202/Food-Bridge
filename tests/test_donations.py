"""Tests for donation service and lifecycle."""
from datetime import datetime, timedelta
from app.models.donation import Donation, DonationStatus, FoodType, QuantityUnit
from app.services.donation_service import DonationService


def test_create_donation_service(app, donor_user):
    with app.app_context():
        now = datetime.utcnow()
        data = {
            "food_name": "Test Rice Box",
            "food_type": FoodType.COOKED,
            "description": "Delicious fried rice",
            "quantity": 10.0,
            "quantity_unit": QuantityUnit.KG,
            "servings": 40,
            "prepared_at": now - timedelta(hours=1),
            "expiry_at": now + timedelta(hours=12),
            "pickup_address": "123 Main St",
            "latitude": 37.7749,
            "longitude": -122.4194,
        }
        donation = DonationService.create_donation(donor_user.id, data)
        assert donation.id is not None
        assert donation.food_name == "Test Rice Box"
        assert donation.status == DonationStatus.AVAILABLE
        assert donation.hours_until_expiry > 0


def test_expire_stale_donations(app, donor_user):
    with app.app_context():
        past = datetime.utcnow() - timedelta(hours=2)
        d = Donation(
            donor_id=donor_user.id,
            food_name="Old Sandwich",
            food_type=FoodType.COOKED,
            quantity=5.0,
            quantity_unit=QuantityUnit.PORTIONS,
            servings=5,
            prepared_at=past - timedelta(hours=5),
            expiry_at=past,
            pickup_address="123 Street",
            status=DonationStatus.AVAILABLE,
        )
        from app.extensions import db
        db.session.add(d)
        db.session.commit()

        expired_count = DonationService.expire_stale_donations()
        assert expired_count == 1
        assert d.status == DonationStatus.EXPIRED
