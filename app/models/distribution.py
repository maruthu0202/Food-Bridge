"""Distribution record — tracks impact after food is delivered."""
from datetime import datetime
from app.extensions import db


class Distribution(db.Model):
    __tablename__ = "distributions"

    id = db.Column(db.Integer, primary_key=True)
    pickup_request_id = db.Column(
        db.Integer, db.ForeignKey("pickup_requests.id"),
        nullable=False, unique=True, index=True
    )

    quantity_distributed = db.Column(db.Float, nullable=False)
    quantity_unit = db.Column(db.String(30), nullable=False)
    people_served = db.Column(db.Integer, nullable=False, default=0)
    delivered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    remarks = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    pickup_request = db.relationship("PickupRequest", back_populates="distribution")

    def __repr__(self):
        return (
            f"<Distribution {self.id} req={self.pickup_request_id} "
            f"served={self.people_served}>"
        )
