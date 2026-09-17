"""Miscellaneous helpers and Jinja2 template filters."""
from datetime import datetime
from flask import request


def get_client_ip() -> str:
    """Return client IP, handling X-Forwarded-For from App Engine."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def format_datetime(dt: datetime, fmt: str = "%d %b %Y, %H:%M") -> str:
    if dt is None:
        return "—"
    return dt.strftime(fmt)


def time_until(dt: datetime) -> str:
    """Human-readable time remaining until dt."""
    if dt is None:
        return "—"
    delta = dt - datetime.utcnow()
    total_seconds = int(delta.total_seconds())
    if total_seconds <= 0:
        return "Expired"
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    if hours >= 24:
        days = hours // 24
        return f"{days}d {hours % 24}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def register_template_filters(app):
    """Register custom Jinja2 filters on the app."""
    app.jinja_env.filters["datetime"] = format_datetime
    app.jinja_env.filters["time_until"] = time_until
    app.jinja_env.globals["now"] = datetime.utcnow


def paginate_query(query, page: int, per_page: int):
    """Paginate a SQLAlchemy query safely."""
    page = max(1, page)
    return query.paginate(page=page, per_page=per_page, error_out=False)
