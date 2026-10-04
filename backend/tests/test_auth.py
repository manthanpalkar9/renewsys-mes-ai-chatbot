import pytest
from fastapi.testclient import TestClient

def test_login_success(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin_test", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "admin"

def test_login_failure(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin_test", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_get_me(client: TestClient, user_token: str):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "user_test"
    assert data["role"] == "user"
