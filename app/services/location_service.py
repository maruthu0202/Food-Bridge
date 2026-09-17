"""LocationService — Haversine distance calculation and radius filtering.

No external APIs required. Pure Python math.
"""
import math
from typing import List, Tuple, Optional


class LocationService:
    EARTH_RADIUS_KM = 6371.0

    @staticmethod
    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Return great-circle distance in kilometres between two points."""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat / 2) ** 2 + (
            math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))
        return LocationService.EARTH_RADIUS_KM * c

    @staticmethod
    def distance_between(
        point1: Tuple[Optional[float], Optional[float]],
        point2: Tuple[Optional[float], Optional[float]],
    ) -> Optional[float]:
        """Return distance in km between two (lat, lon) tuples, or None if coords missing."""
        lat1, lon1 = point1
        lat2, lon2 = point2
        if any(v is None for v in [lat1, lon1, lat2, lon2]):
            return None
        return LocationService.haversine(lat1, lon1, lat2, lon2)

    @staticmethod
    def filter_by_radius(
        center_lat: float,
        center_lon: float,
        items,
        radius_km: float = 25.0,
        lat_attr: str = "latitude",
        lon_attr: str = "longitude",
    ) -> List[Tuple[float, object]]:
        """Filter a list of ORM objects by radius and return (distance, item) tuples sorted by distance."""
        results = []
        for item in items:
            item_lat = getattr(item, lat_attr, None)
            item_lon = getattr(item, lon_attr, None)
            if item_lat is None or item_lon is None:
                # Include items without coordinates at the end with a large distance
                results.append((99999.0, item))
                continue
            dist = LocationService.haversine(center_lat, center_lon, item_lat, item_lon)
            if dist <= radius_km:
                results.append((dist, item))

        results.sort(key=lambda x: x[0])
        return results

    @staticmethod
    def bounding_box(lat: float, lon: float, radius_km: float):
        """Return approximate (min_lat, max_lat, min_lon, max_lon) bounding box for a DB pre-filter."""
        delta_lat = radius_km / LocationService.EARTH_RADIUS_KM
        delta_lon = radius_km / (
            LocationService.EARTH_RADIUS_KM * math.cos(math.radians(lat))
        )
        delta_lat = math.degrees(delta_lat)
        delta_lon = math.degrees(delta_lon)
        return (
            lat - delta_lat,
            lat + delta_lat,
            lon - delta_lon,
            lon + delta_lon,
        )
