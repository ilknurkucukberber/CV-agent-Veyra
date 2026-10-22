from fastapi.testclient import TestClient


def test_salary_estimate_known_position(client: TestClient, auth_headers: dict[str, str]):
    payload = {
        "position": "Software Engineer",
        "city": "Istanbul",
        "experience_level": "mid",
    }
    response = client.post("/api/v1/salary/estimate", json=payload, headers=auth_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["range_low"] < data["range_mid"] < data["range_high"]
    assert data["source"]
    assert data["source_date"]


def test_salary_estimate_unknown_position_returns_404_when_provider_fails(
    client: TestClient, auth_headers: dict[str, str], monkeypatch
):
    from app.core.llm import LLMError

    def unavailable(*args, **kwargs):
        raise LLMError("Provider unavailable")

    monkeypatch.setattr("app.api.routes.salary.estimate_salary_with_llm", unavailable)
    payload = {
        "position": "Astronaut",
        "city": "Istanbul",
        "experience_level": "mid",
    }
    response = client.post("/api/v1/salary/estimate", json=payload, headers=auth_headers)
    assert response.status_code == 404


def test_salary_estimate_requires_auth(client: TestClient):
    response = client.post(
        "/api/v1/salary/estimate",
        json={"position": "Software Engineer", "city": "Istanbul", "experience_level": "mid"},
    )
    assert response.status_code == 401
