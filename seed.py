"""Database Seeder — Populates demo data for development and testing."""
from datetime import datetime, timedelta
import logging

from app import create_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.donation import Donation, DonationStatus, FoodType, QuantityUnit
from app.models.pickup_request import PickupRequest, RequestStatus
from app.models.distribution import Distribution
from app.models.audit_log import AuditLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seeder")


def seed_database():
    app = create_app()
    with app.app_context():
        logger.info("Dropping existing tables and recreating clean schema...")
        db.drop_all()
        db.create_all()

        logger.info("Seeding users...")

        # 1. Admin User
        admin = User(
            email="admin@foodbridge.org",
            full_name="System Administrator",
            role=UserRole.ADMIN,
            phone="+1-555-0100",
            address="100 Tech Plaza, Metropolis",
            is_active=True,
            is_verified=True,
        )
        admin.set_password("Admin@123")
        db.session.add(admin)

        # 2. Donor 1 (City Bakery)
        donor1 = User(
            email="donor@citybakery.com",
            full_name="Alice Artisan",
            org_name="City Bakery & Cafe",
            role=UserRole.DONOR,
            phone="+1-555-0101",
            address="742 Evergreen Terrace, Springfield",
            latitude=37.7749,
            longitude=-122.4194,
            is_active=True,
            is_verified=True,
        )
        donor1.set_password("Donor@123")
        db.session.add(donor1)

        # 3. Donor 2 (Metro Hotel)
        donor2 = User(
            email="manager@metrohotel.com",
            full_name="Bob Builder",
            org_name="Metro Grand Hotel",
            role=UserRole.DONOR,
            phone="+1-555-0102",
            address="500 Ocean Drive, Bay City",
            latitude=37.7833,
            longitude=-122.4167,
            is_active=True,
            is_verified=True,
        )
        donor2.set_password("Donor@123")
        db.session.add(donor2)

        # 4. NGO 1 (Hope Shelter)
        ngo1 = User(
            email="ngo@hopeshelter.org",
            full_name="Carol Director",
            org_name="Hope Shelter Foundation",
            org_description="Providing hot meals and emergency assistance to urban homeless communities.",
            role=UserRole.NGO,
            phone="+1-555-0103",
            address="120 Community Way, Springfield",
            latitude=37.7755,
            longitude=-122.4180,
            is_active=True,
            is_verified=True,
        )
        ngo1.set_password("Ngo@123")
        db.session.add(ngo1)

        # 5. NGO 2 (Food First)
        ngo2 = User(
            email="contact@foodfirst.org",
            full_name="David Coordinator",
            org_name="Food First Network",
            org_description="Connecting excess grocery store inventory to community pantries.",
            role=UserRole.NGO,
            phone="+1-555-0104",
            address="45 Harvest Lane, Springfield",
            latitude=37.7800,
            longitude=-122.4100,
            is_active=True,
            is_verified=True,
        )
        ngo2.set_password("Ngo@123")
        db.session.add(ngo2)

        db.session.commit()
        logger.info("Users seeded successfully.")

        now = datetime.utcnow()

        logger.info("Seeding donations...")

        # Donation 1: Available Cooked Meals
        d1 = Donation(
            donor_id=donor1.id,
            food_name="Fresh Assorted Muffins & Sandwiches",
            food_type=FoodType.BAKED,
            description="Box of freshly baked breakfast muffins and vegetarian sandwiches prepared this morning.",
            quantity=50.0,
            quantity_unit=QuantityUnit.PORTIONS,
            servings=50,
            prepared_at=now - timedelta(hours=3),
            expiry_at=now + timedelta(hours=18),
            pickup_address="742 Evergreen Terrace, Springfield",
            latitude=37.7749,
            longitude=-122.4194,
            status=DonationStatus.AVAILABLE,
        )

        # Donation 2: Requested Raw Ingredients
        d2 = Donation(
            donor_id=donor2.id,
            food_name="Bulk Rice & Pulses Bags",
            food_type=FoodType.RAW,
            description="Surplus 25kg bags of Basmati rice and whole lentils from catering event.",
            quantity=100.0,
            quantity_unit=QuantityUnit.KG,
            servings=400,
            prepared_at=now - timedelta(days=1),
            expiry_at=now + timedelta(days=7),
            pickup_address="500 Ocean Drive, Bay City",
            latitude=37.7833,
            longitude=-122.4167,
            status=DonationStatus.REQUESTED,
        )

        # Donation 3: Delivered (Completed)
        d3 = Donation(
            donor_id=donor1.id,
            food_name="Hot Vegetable Curry & Rice",
            food_type=FoodType.COOKED,
            description="Freshly cooked vegetable curry with steamed rice in insulated food containers.",
            quantity=30.0,
            quantity_unit=QuantityUnit.KG,
            servings=120,
            prepared_at=now - timedelta(days=2),
            expiry_at=now - timedelta(days=1, hours=12),
            pickup_address="742 Evergreen Terrace, Springfield",
            latitude=37.7749,
            longitude=-122.4194,
            status=DonationStatus.DELIVERED,
        )

        db.session.add_all([d1, d2, d3])
        db.session.commit()
        logger.info("Donations seeded successfully.")

        # Seed Pickup Requests & Distribution
        req1 = PickupRequest(
            donation_id=d2.id,
            ngo_id=ngo1.id,
            notes="We have a van available for immediate pickup today at 3 PM.",
            status=RequestStatus.PENDING,
            requested_at=now - timedelta(hours=2),
        )
        db.session.add(req1)

        req2 = PickupRequest(
            donation_id=d3.id,
            ngo_id=ngo1.id,
            notes="Completed pickup for evening shelter distribution.",
            status=RequestStatus.COMPLETED,
            requested_at=now - timedelta(days=2),
            approved_at=now - timedelta(days=2, hours=1),
            pickup_time=now - timedelta(days=2, hours=2),
        )
        db.session.add(req2)
        db.session.commit()

        dist1 = Distribution(
            pickup_request_id=req2.id,
            quantity_distributed=30.0,
            quantity_unit=QuantityUnit.KG,
            people_served=120,
            delivered_at=now - timedelta(days=2, hours=3),
            remarks="Distributed at Downtown Hope Shelter evening dinner service.",
        )
        db.session.add(dist1)

        # Audit Logs
        log1 = AuditLog(
            user_id=admin.id,
            action="database_seeded",
            details="Seeded initial system demo data.",
        )
        db.session.add(log1)
        db.session.commit()

        logger.info("Database seeded successfully with demo users, donations, requests, and distributions!")


if __name__ == "__main__":
    seed_database()
