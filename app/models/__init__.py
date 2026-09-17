"""Models package — import all models here so Flask-Migrate detects them."""
from app.models.user import User, UserRole
from app.models.donation import Donation, DonationStatus, FoodType, QuantityUnit
from app.models.pickup_request import PickupRequest, RequestStatus
from app.models.distribution import Distribution
from app.models.audit_log import AuditLog

__all__ = [
    "User", "UserRole",
    "Donation", "DonationStatus", "FoodType", "QuantityUnit",
    "PickupRequest", "RequestStatus",
    "Distribution",
    "AuditLog",
]
