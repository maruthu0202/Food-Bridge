"""Pytest fixtures for FoodBridge application testing."""
import pytest
from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models.user import User, UserRole


@pytest.fixture
def app():
    """Create application configured for testing."""
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's CLI commands."""
    return app.test_cli_runner()


@pytest.fixture
def donor_user(app):
    """Create a sample Donor user."""
    user = User(
        email="donor@example.com",
        full_name="Test Donor",
        role=UserRole.DONOR,
        is_active=True,
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def ngo_user(app):
    """Create a sample NGO user."""
    user = User(
        email="ngo@example.com",
        full_name="Test NGO",
        org_name="Hope NGO",
        role=UserRole.NGO,
        is_active=True,
        latitude=37.7749,
        longitude=-122.4194,
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def admin_user(app):
    """Create a sample Admin user."""
    user = User(
        email="admin@example.com",
        full_name="Test Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user
