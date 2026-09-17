"""Application factory — creates and configures the Flask app."""
import logging
import os

from flask import Flask, render_template

from app.config import get_config
from app.extensions import csrf, db, login_manager, migrate
from app.services.storage_service import storage_service
from app.utils.helpers import register_template_filters


def create_app(config_object=None):
    app = Flask(__name__)

    # Load configuration
    if config_object is None:
        config_object = get_config()
    app.config.from_object(config_object)

    # Ensure local upload directory exists
    os.makedirs(app.config["LOCAL_UPLOAD_FOLDER"], exist_ok=True)
    storage_service.init_app(app)

    # Initialise extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Register Jinja2 template filters
    register_template_filters(app)

    # Automatically create tables if using SQLite or dev environment
    with app.app_context():
        from app.models.user import User  # noqa: F401
        from app.models.donation import Donation  # noqa: F401
        from app.models.pickup_request import PickupRequest  # noqa: F401
        from app.models.distribution import Distribution  # noqa: F401
        from app.models.audit_log import AuditLog  # noqa: F401
        db.create_all()

    # Configure logging
    _configure_logging(app)

    # Register user loader
    from app.models.user import User  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.donor import donor_bp
    from app.routes.ngo import ngo_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(donor_bp, url_prefix="/donor")
    app.register_blueprint(ngo_bp, url_prefix="/ngo")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    # Register error handlers
    _register_error_handlers(app)

    return app


def _configure_logging(app):
    level = logging.DEBUG if app.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app.logger.setLevel(level)


def _register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/400.html"), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return render_template("errors/401.html"), 401

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(409)
    def conflict(e):
        return render_template("errors/409.html"), 409

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        app.logger.exception("Internal server error")
        return render_template("errors/500.html"), 500
