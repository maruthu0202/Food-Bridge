"""Role-based access control decorators."""
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def donor_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_donor:
            abort(403)
        if not current_user.is_active:
            flash("Your account has been suspended.", "danger")
            return redirect(url_for("auth.logout"))
        return f(*args, **kwargs)
    return decorated


def ngo_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_ngo:
            abort(403)
        if not current_user.is_active:
            flash("Your account has been suspended.", "danger")
            return redirect(url_for("auth.logout"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def active_required(f):
    """Ensure the user account is not suspended."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_active:
            flash("Your account has been suspended. Contact support.", "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)
    return decorated
