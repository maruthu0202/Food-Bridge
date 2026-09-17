"""PickupRequest model — one active request per donation at a time."""
from datetime import datetime
from app.extensions import db


class RequestStatus:
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    PICKED_UP = "PICKED_UP"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

    TRANSITIONS = {
        PENDING: [ACCEPTED, REJECTED, CANCELLED],
        ACCEPTED: [READY_FOR_PICKUP, CANCELLED],
        READY_FOR_PICKUP: [PICKED_UP, CANCELLED],
        PICKED_UP: [COMPLETED],
        COMPLETED: [],
        REJECTED: [],
        CANCELLED: [],
    }

    TERMINAL = [COMPLETED, REJECTED, CANCELLED]
    ACTIVE = [PENDING, ACCEPTED, READY_FOR_PICKUP, PICKED_UP]


class PickupRequest(db.Model):
    __tablename__ = "pickup_requests"

    id = db.Column(db.Integer, primary_key=True)
    donation_id = db.Column(db.Integer, db.ForeignKey("donations.id"),
                            nullable=False, index=True)
    ngo_id = db.Column(db.Integer, db.ForeignKey("users.id"),
                       nullable=False, index=True)

    requested_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    approved_at = db.Column(db.DateTime, nullable=True)
    pickup_time = db.Column(db.DateTime, nullable=True)

    status = db.Column(
        db.String(30),
        nullable=False,
        default=RequestStatus.PENDING,
        index=True,
    )
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    donation = db.relationship("Donation", back_populates="pickup_requests")
    ngo = db.relationship("User", back_populates="pickup_requests",
                          foreign_keys=[ngo_id])
    distribution = db.relationship("Distribution", back_populates="pickup_request",
                                   uselist=False)

    # ------------------------------------------------------------------ #
    #  State machine                                                        #
    # ------------------------------------------------------------------ #

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in RequestStatus.TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status: str):
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Invalid request transition: {self.status} → {new_status}"
            )
        self.status = new_status
        if new_status == RequestStatus.ACCEPTED:
            self.approved_at = datetime.utcnow()
        if new_status == RequestStatus.PICKED_UP:
            self.pickup_time = datetime.utcnow()

    @property
    def status_badge_class(self) -> str:
        mapping = {
            RequestStatus.PENDING: "warning",
            RequestStatus.ACCEPTED: "info",
            RequestStatus.READY_FOR_PICKUP: "primary",
            RequestStatus.PICKED_UP: "secondary",
            RequestStatus.COMPLETED: "success",
            RequestStatus.REJECTED: "danger",
            RequestStatus.CANCELLED: "danger",
        }
        return mapping.get(self.status, "secondary")

    def __repr__(self):
        return f"<PickupRequest {self.id} donation={self.donation_id} [{self.status}]>"
