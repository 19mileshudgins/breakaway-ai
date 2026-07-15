import pytest
from fastapi.testclient import TestClient
from submission_frontend.main import app

client = TestClient(app)

def test_get_dashboard_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "ADK Manager Approval Dashboard" in response.text
    assert "glassmorphism" in response.text or "Outfit" in response.text

def test_get_pending_approvals():
    response = client.get("/api/pending")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "pending_approvals" in data
    assert len(data["pending_approvals"]) > 0

def test_post_approve_action():
    payload = {"approved": True, "interrupt_id": "intr_001_peak_load"}
    response = client.post("/api/action/sess_98214a_workout_plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["session_id"] == "sess_98214a_workout_plan"
    assert data["user_id"] == "default-user"
    assert data["action"] == "APPROVED"

def test_post_reject_action():
    payload = {"approved": False, "interrupt_id": "intr_002_power_meter"}
    response = client.post("/api/action/sess_47219b_equipment_stipend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["action"] == "REJECTED"
