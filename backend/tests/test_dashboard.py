from fastapi.testclient import TestClient


def test_dashboard_summary_empty_state(client: TestClient, auth_headers: dict[str, str]):
    response = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["profile_completion_percentage"] == 0
    assert data["active_applications_count"] == 0
    assert data["cv_version_count"] == 0
    assert data["ats_score"] is None
    assert data["status_distribution"] == {}
    assert data["upcoming_interviews"] == []


def test_dashboard_summary_reflects_applications(client: TestClient, auth_headers: dict[str, str]):
    client.post(
        "/api/v1/applications",
        json={"company": "Acme", "position": "Backend Developer", "status": "hr_interview"},
        headers=auth_headers,
    )

    response = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["active_applications_count"] == 1
    assert data["status_distribution"] == {"hr_interview": 1}
    assert len(data["upcoming_interviews"]) == 1
    assert data["upcoming_interviews"][0]["company"] == "Acme"


def test_dashboard_requires_auth(client: TestClient):
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 401
