"""User model with role-based access control."""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class UserRole:
    DONOR = "DONOR"
    NGO = "NGO"
    ADMIN = "ADMIN"

    ALL = [DONOR, NGO, ADMIN]


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=UserRole.DONOR)

    # Common profile fields
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(500), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    # NGO-specific
    org_name = db.Column(db.String(200), nullable=True)
    org_description = db.Column(db.Text, nullable=True)

    # Account state
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    donations = db.relationship("Donation", back_populates="donor",
                                lazy="dynamic", foreign_keys="Donation.donor_id")
    pickup_requests = db.relationship("PickupRequest", back_populates="ngo",
                                      lazy="dynamic", foreign_keys="PickupRequest.ngo_id")
    audit_logs = db.relationship("AuditLog", back_populates="user", lazy="dynamic")

    # ------------------------------------------------------------------ #
    #  Password management                                                  #
    # ------------------------------------------------------------------ #

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # ------------------------------------------------------------------ #
    #  Role helpers                                                         #
    # ------------------------------------------------------------------ #

    @property
    def is_donor(self) -> bool:
        return self.role == UserRole.DONOR

    @property
    def is_ngo(self) -> bool:
        return self.role == UserRole.NGO

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def display_name(self) -> str:
        return self.org_name if (self.is_ngo and self.org_name) else self.full_name

    def __repr__(self):
        return f"<User {self.email} [{self.role}]>"
