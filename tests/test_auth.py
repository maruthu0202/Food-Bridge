"""Tests for authentication workflows."""

def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"FoodBridge" in response.data


def test_register_and_login(client):
    # Register Donor
    res = client.post("/auth/register", data={
        "email": "newdonor@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "full_name": "New Donor",
        "role": "DONOR",
        "phone": "+1-555-9999",
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Registration successful" in res.data

    # Login
    login_res = client.post("/auth/login", data={
        "email": "newdonor@example.com",
        "password": "Password123!",
    }, follow_redirects=True)
    assert login_res.status_code == 200
    assert b"Dashboard" in login_res.data or b"My Donations" in login_res.data


def test_login_invalid_password(client, donor_user):
    res = client.post("/auth/login", data={
        "email": donor_user.email,
        "password": "WrongPassword",
    })
    assert res.status_code == 200
    assert b"Invalid email or password" in res.data
