import pytest
from fastapi.testclient import TestClient

def test_create_session(client: TestClient, user_token: str):
    response = client.post(
        "/api/v1/chat/session",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data

def test_chat_message(client: TestClient, user_token: str):
    sess_resp = client.post(
        "/api/v1/chat/session",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    session_id = sess_resp.json()["session_id"]
    
    msg_resp = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "session_id": session_id,
            "message": "What is the total production for KM1 today?"
        }
    )
    assert msg_resp.status_code == 200
    data = msg_resp.json()
    assert data["session_id"] == session_id
    assert "answer" in data
    assert "data_freshness" in data

def test_profit_question_blocked(client: TestClient, user_token: str):
    sess_resp = client.post(
        "/api/v1/chat/session",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    session_id = sess_resp.json()["session_id"]
    
    msg_resp = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "session_id": session_id,
            "message": "What is the profit margin for line KM2?"
        }
    )
    assert msg_resp.status_code == 200
    data = msg_resp.json()
    assert "cannot answer questions about profit" in data["answer"].lower()

def test_sql_visibility_rbac(client: TestClient, admin_token: str, user_token: str):
    admin_sess = client.post("/api/v1/chat/session", headers={"Authorization": f"Bearer {admin_token}"})
    user_sess = client.post("/api/v1/chat/session", headers={"Authorization": f"Bearer {user_token}"})
    
    msg = "How many modules produced today?"
    
    admin_msg = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"session_id": admin_sess.json()["session_id"], "message": msg}
    )
    if admin_msg.json().get("response_type") == "kpi_card":
        assert admin_msg.json().get("generated_sql") is not None
    
    user_msg = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"session_id": user_sess.json()["session_id"], "message": msg}
    )
    assert user_msg.json().get("generated_sql") is None
