"""Tests for JSON API endpoints."""
from datetime import datetime, timedelta
from app.models.donation import FoodType, QuantityUnit
from app.services.donation_service import DonationService


def test_api_list_donations(client, donor_user):
    # Create donation via service
    now = datetime.utcnow()
    with client.application.app_context():
        DonationService.create_donation(donor_user.id, {
            "food_name": "API Test Pasta",
            "food_type": FoodType.COOKED,
            "quantity": 5.0,
            "quantity_unit": QuantityUnit.KG,
            "servings": 15,
            "prepared_at": now - timedelta(hours=1),
            "expiry_at": now + timedelta(hours=10),
            "pickup_address": "789 Broadway",
        })

    res = client.get("/api/donations")
    assert res.status_code == 200
    data = res.get_json()
    assert "donations" in data
    assert len(data["donations"]) >= 1
    assert data["donations"][0]["food_name"] == "API Test Pasta"
