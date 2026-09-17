"""Server-side validators for form inputs."""
import re
from datetime import datetime
from typing import Optional, Tuple


PASSWORD_MIN_LENGTH = 8
PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#^()\-_=+]).{8,}$"
)
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    if not email or len(email) > 255:
        return False, "Email must be between 1 and 255 characters."
    if not EMAIL_REGEX.match(email.strip()):
        return False, "Please enter a valid email address."
    return True, None


def validate_password(password: str) -> Tuple[bool, Optional[str]]:
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
    if not PASSWORD_REGEX.match(password):
        return (
            False,
            "Password must contain uppercase, lowercase, a digit, and a special character.",
        )
    return True, None


def validate_registration(data: dict) -> list:
    """Return list of error strings."""
    errors = []
    ok, msg = validate_email(data.get("email", ""))
    if not ok:
        errors.append(msg)
    ok, msg = validate_password(data.get("password", ""))
    if not ok:
        errors.append(msg)
    if data.get("password") != data.get("confirm_password"):
        errors.append("Passwords do not match.")
    if not data.get("full_name", "").strip():
        errors.append("Full name is required.")
    if len(data.get("full_name", "")) > 150:
        errors.append("Full name must be under 150 characters.")
    role = data.get("role", "")
    if role not in ["DONOR", "NGO"]:
        errors.append("Invalid role selected.")
    return errors


def validate_donation(data: dict) -> list:
    errors = []
    if not data.get("food_name", "").strip():
        errors.append("Food name is required.")
    if len(data.get("food_name", "")) > 200:
        errors.append("Food name must be under 200 characters.")
    try:
        qty = float(data.get("quantity", 0))
        if qty <= 0:
            errors.append("Quantity must be positive.")
    except (TypeError, ValueError):
        errors.append("Quantity must be a number.")
    try:
        srv = int(data.get("servings", 0))
        if srv <= 0:
            errors.append("Servings must be a positive integer.")
    except (TypeError, ValueError):
        errors.append("Servings must be a whole number.")
    if not data.get("pickup_address", "").strip():
        errors.append("Pickup address is required.")

    # Date validation
    prepared_at = data.get("prepared_at")
    expiry_at = data.get("expiry_at")
    if isinstance(prepared_at, str):
        try:
            prepared_at = datetime.fromisoformat(prepared_at)
        except ValueError:
            errors.append("Invalid preparation date/time.")
    if isinstance(expiry_at, str):
        try:
            expiry_at = datetime.fromisoformat(expiry_at)
        except ValueError:
            errors.append("Invalid expiry date/time.")
    if isinstance(prepared_at, datetime) and isinstance(expiry_at, datetime):
        if expiry_at <= prepared_at:
            errors.append("Expiry time must be after preparation time.")
        if expiry_at <= datetime.utcnow():
            errors.append("Expiry time must be in the future.")
    return errors


def validate_lat_lon(lat, lon) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """Parse and validate lat/lon. Returns (lat, lon, error_message)."""
    try:
        lat = float(lat) if lat not in (None, "") else None
        lon = float(lon) if lon not in (None, "") else None
    except (TypeError, ValueError):
        return None, None, "Latitude and longitude must be numbers."
    if lat is not None and not (-90 <= lat <= 90):
        return None, None, "Latitude must be between -90 and 90."
    if lon is not None and not (-180 <= lon <= 180):
        return None, None, "Longitude must be between -180 and 180."
    return lat, lon, None
