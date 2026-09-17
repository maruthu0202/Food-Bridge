"""Donation model with full status state machine."""
from datetime import datetime
from app.extensions import db


class FoodType:
    COOKED = "Cooked Meal"
    RAW = "Raw Ingredients"
    BAKED = "Baked Goods"
    BEVERAGES = "Beverages"
    PACKAGED = "Packaged Food"
    FRUITS_VEG = "Fruits & Vegetables"
    DAIRY = "Dairy Products"
    OTHER = "Other"

    ALL = [COOKED, RAW, BAKED, BEVERAGES, PACKAGED, FRUITS_VEG, DAIRY, OTHER]


class DonationStatus:
    AVAILABLE = "AVAILABLE"
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    PICKED_UP = "PICKED_UP"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

    # Valid forward transitions
    TRANSITIONS = {
        AVAILABLE: [REQUESTED, CANCELLED],
        REQUESTED: [ACCEPTED, CANCELLED, AVAILABLE],   # AVAILABLE if request rejected
        ACCEPTED: [READY_FOR_PICKUP, CANCELLED],
        READY_FOR_PICKUP: [PICKED_UP, CANCELLED],
        PICKED_UP: [DELIVERED],
        DELIVERED: [],
        CANCELLED: [],
        EXPIRED: [],
    }

    TERMINAL = [DELIVERED, CANCELLED, EXPIRED]
    ACTIVE = [AVAILABLE, REQUESTED, ACCEPTED, READY_FOR_PICKUP, PICKED_UP]


class QuantityUnit:
    KG = "kg"
    GRAMS = "grams"
    LITRES = "litres"
    PACKETS = "packets"
    BOXES = "boxes"
    PORTIONS = "portions"
    PIECES = "pieces"

    ALL = [KG, GRAMS, LITRES, PACKETS, BOXES, PORTIONS, PIECES]


class Donation(db.Model):
    __tablename__ = "donations"

    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    food_name = db.Column(db.String(200), nullable=False)
    food_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    quantity = db.Column(db.Float, nullable=False)
    quantity_unit = db.Column(db.String(30), nullable=False)
    servings = db.Column(db.Integer, nullable=False)

    prepared_at = db.Column(db.DateTime, nullable=False)
    expiry_at = db.Column(db.DateTime, nullable=False, index=True)

    pickup_address = db.Column(db.String(500), nullable=False)
    latitude = db.Column(db.Float, nullable=True, index=True)
    longitude = db.Column(db.Float, nullable=True, index=True)

    image_path = db.Column(db.String(1000), nullable=True)

    status = db.Column(
        db.String(30),
        nullable=False,
        default=DonationStatus.AVAILABLE,
        index=True,
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow, nullable=False)

    # Relationships
    donor = db.relationship("User", back_populates="donations", foreign_keys=[donor_id])
    pickup_requests = db.relationship("PickupRequest", back_populates="donation",
                                      lazy="dynamic")

    # ------------------------------------------------------------------ #
    #  State machine helpers                                                #
    # ------------------------------------------------------------------ #

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in DonationStatus.TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status: str):
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Invalid transition: {self.status} → {new_status}"
            )
        self.status = new_status
        self.updated_at = datetime.utcnow()

    # ------------------------------------------------------------------ #
    #  Computed properties                                                  #
    # ------------------------------------------------------------------ #

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expiry_at

    @property
    def is_active(self) -> bool:
        return self.status in DonationStatus.ACTIVE

    @property
    def hours_until_expiry(self) -> float:
        delta = self.expiry_at - datetime.utcnow()
        return max(0.0, delta.total_seconds() / 3600)

    @property
    def status_badge_class(self) -> str:
        mapping = {
            DonationStatus.AVAILABLE: "success",
            DonationStatus.REQUESTED: "warning",
            DonationStatus.ACCEPTED: "info",
            DonationStatus.READY_FOR_PICKUP: "primary",
            DonationStatus.PICKED_UP: "secondary",
            DonationStatus.DELIVERED: "dark",
            DonationStatus.CANCELLED: "danger",
            DonationStatus.EXPIRED: "danger",
        }
        return mapping.get(self.status, "secondary")

    def __repr__(self):
        return f"<Donation {self.id} '{self.food_name}' [{self.status}]>"
