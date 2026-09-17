"""DonationMatchingService — ranks available donations for an NGO.

Scoring factors (all normalised to 0-1):
  1. distance_score   — closer is better
  2. expiry_score     — more urgent expiry scores higher (so NGO can save it in time)
  3. quantity_score   — more servings is better

Final priority = weighted sum. Weights are configurable.
"""
from typing import List, Tuple, Optional
from app.services.location_service import LocationService
from app.models.donation import Donation


class DonationMatchingService:
    DEFAULT_WEIGHTS = {
        "distance": 0.5,
        "expiry": 0.35,
        "quantity": 0.15,
    }

    MAX_DISTANCE_KM = 50.0     # distances beyond this score 0
    MAX_HOURS_TO_EXPIRY = 48.0  # window considered for expiry scoring

    @classmethod
    def rank_donations(
        cls,
        donations: List[Donation],
        ngo_lat: Optional[float],
        ngo_lon: Optional[float],
        radius_km: float = 25.0,
        weights: Optional[dict] = None,
    ) -> List[Tuple[float, float, Donation]]:
        """Return list of (score, distance_km, donation) sorted by score descending."""
        if weights is None:
            weights = cls.DEFAULT_WEIGHTS

        results = []
        for donation in donations:
            distance_km = None
            if ngo_lat and ngo_lon:
                distance_km = LocationService.distance_between(
                    (ngo_lat, ngo_lon),
                    (donation.latitude, donation.longitude),
                )

            # Skip if outside radius and both have coordinates
            if distance_km is not None and distance_km > radius_km:
                continue

            score = cls._compute_score(donation, distance_km, weights)
            results.append((score, distance_km or 0.0, donation))

        results.sort(key=lambda x: x[0], reverse=True)
        return results

    @classmethod
    def _compute_score(
        cls,
        donation: Donation,
        distance_km: Optional[float],
        weights: dict,
    ) -> float:
        # 1. Distance score (1 = very close, 0 = at max distance)
        if distance_km is None:
            dist_score = 0.5  # neutral when no coords available
        else:
            dist_score = max(0.0, 1.0 - (distance_km / cls.MAX_DISTANCE_KM))

        # 2. Expiry score (1 = expiring very soon, 0 = plenty of time)
        hours = donation.hours_until_expiry
        if hours <= 0:
            expiry_score = 0.0  # already expired
        elif hours >= cls.MAX_HOURS_TO_EXPIRY:
            expiry_score = 0.1  # lots of time — low urgency
        else:
            expiry_score = 1.0 - (hours / cls.MAX_HOURS_TO_EXPIRY)

        # 3. Quantity score (more servings = slightly preferred)
        qty_score = min(1.0, donation.servings / 200.0)

        score = (
            weights.get("distance", 0.5) * dist_score
            + weights.get("expiry", 0.35) * expiry_score
            + weights.get("quantity", 0.15) * qty_score
        )
        return round(score, 4)
