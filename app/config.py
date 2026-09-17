import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration shared by all environments."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    WTF_CSRF_ENABLED = True

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,
        "pool_pre_ping": True,
    }

    # File uploads
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    # Google Cloud Storage
    GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "")

    # Local upload fallback (used when GCS not configured)
    LOCAL_UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

    # Pagination
    DONATIONS_PER_PAGE = 12
    REQUESTS_PER_PAGE = 20

    # Distance filter default (km)
    DEFAULT_SEARCH_RADIUS_KM = 25


class DevelopmentConfig(Config):
    DEBUG = True
    _db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "food_donation_dev.db")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{_db_path}",
    )
    # In dev, keep session cookies without HTTPS requirement
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

    # Cloud SQL via Unix socket (App Engine)
    _db_user = os.environ.get("DB_USER", "")
    _db_pass = os.environ.get("DB_PASS", "")
    _db_name = os.environ.get("DB_NAME", "food_donation_prod")
    _cloud_sql_connection = os.environ.get("CLOUD_SQL_CONNECTION_NAME", "")

    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or (
            f"mysql+pymysql://{_db_user}:{_db_pass}@/{_db_name}"
            f"?unix_socket=/cloudsql/{_cloud_sql_connection}"
            if _cloud_sql_connection
            else f"mysql+pymysql://{_db_user}:{_db_pass}@localhost:3306/{_db_name}"
        )
    )

    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PREFERRED_URL_SCHEME = "https"


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # Use local storage in tests
    GCS_BUCKET_NAME = ""


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
