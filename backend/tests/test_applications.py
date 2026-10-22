from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def test_application_crud_and_prep_checklist(client: TestClient, auth_headers: dict[str, str]):
    app_data = {"company": "Google", "position": "Software Engineer", "status": "saved"}
    response = client.post("/api/v1/applications", json=app_data, headers=auth_headers)
    assert response.status_code == 200, response.text
    app_id = response.json()["id"]

    response = client.get(f"/api/v1/applications/{app_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["company"] == "Google"

    response = client.patch(
        f"/api/v1/applications/{app_id}", json={"status": "applied"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "applied"

    response = client.get("/api/v1/applications", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Prep-checklist without a linked resume version should fail with 400.
    response = client.get(f"/api/v1/applications/{app_id}/prep-checklist", headers=auth_headers)
    assert response.status_code == 400

    response = client.delete(f"/api/v1/applications/{app_id}", headers=auth_headers)
    assert response.status_code == 200

    response = client.get(f"/api/v1/applications/{app_id}", headers=auth_headers)
    assert response.status_code == 404


def test_applications_require_auth(client: TestClient):
    response = client.get("/api/v1/applications")
    assert response.status_code == 401


def _create(client: TestClient, headers: dict[str, str], status: str, company: str = "X Corp"):
    return client.post(
        "/api/v1/applications",
        json={"company": company, "position": "Engineer", "status": status},
        headers=headers,
    )


class TestFunnelAnalytics:
    def test_funnel_is_empty_with_no_applications(
        self, client: TestClient, auth_headers: dict[str, str]
    ):
        resp = client.get("/api/v1/applications/analytics/funnel", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == 0
        assert all(stage["count"] == 0 for stage in body["stages"])

    def test_funnel_counts_are_cumulative_and_rejected_is_separate(
        self, client: TestClient, auth_headers: dict[str, str]
    ):
        for status in ["saved", "applied", "hr_interview", "technical_interview", "offer", "rejected"]:
            resp = _create(client, auth_headers, status)
            assert resp.status_code == 200, resp.text

        body = client.get("/api/v1/applications/analytics/funnel", headers=auth_headers).json()
        by_key = {s["key"]: s["count"] for s in body["stages"]}

        # 6 başvurudan 1'i rejected (ayrı sayılır); geri kalan 5'i saved
        # aşamasına ulaşmıştır (en düşük ortak payda).
        assert by_key["saved"] == 5
        assert by_key["applied"] == 4
        assert by_key["hr_interview"] == 3
        assert by_key["technical_interview"] == 2
        assert by_key["offer"] == 1
        assert body["rejected_count"] == 1
        assert body["total_count"] == 6

    def test_funnel_only_reflects_own_applications(
        self, client: TestClient, auth_headers: dict[str, str]
    ):
        from tests.fixtures import register_and_login

        _create(client, auth_headers, "offer")

        other_token = register_and_login(
            client, {"email": "other@example.com", "password": "sifre1234"}
        )
        other_headers = {"Authorization": f"Bearer {other_token}"}
        body = client.get("/api/v1/applications/analytics/funnel", headers=other_headers).json()
        assert body["total_count"] == 0


class TestReminderDigest:
    def test_trigger_returns_zero_when_nothing_due(
        self, client: TestClient, auth_headers: dict[str, str]
    ):
        _create(client, auth_headers, "saved")
        resp = client.post(
            "/api/v1/applications/analytics/trigger-reminder-digest", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["users_notified"] == 0

    def test_trigger_notifies_for_upcoming_interview_then_respects_cooldown(
        self, client: TestClient, auth_headers: dict[str, str]
    ):
        app_id = _create(client, auth_headers, "hr_interview").json()["id"]
        soon = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()
        resp = client.patch(
            f"/api/v1/applications/{app_id}", json={"interview_at": soon}, headers=auth_headers
        )
        assert resp.status_code == 200

        resp = client.post(
            "/api/v1/applications/analytics/trigger-reminder-digest", headers=auth_headers
        )
        assert resp.json()["users_notified"] == 1

        # Aynı hatırlatmayı hemen tekrar tetiklemek kimseyi bildirmemeli
        # (cooldown penceresi içinde).
        resp = client.post(
            "/api/v1/applications/analytics/trigger-reminder-digest", headers=auth_headers
        )
        assert resp.json()["users_notified"] == 0

    def test_trigger_notifies_for_stale_application(
        self, client: TestClient, auth_headers: dict[str, str]
    ):
        from app.models import Application
        from tests.conftest import TestingSessionLocal

        app_id = _create(client, auth_headers, "applied").json()["id"]

        # 20 gün önce güncellenmiş gibi işaretle (hiç ilerleme kaydedilmemiş).
        db = TestingSessionLocal()
        try:
            application = db.get(Application, app_id)
            application.updated_at = datetime.now(timezone.utc) - timedelta(days=20)
            db.commit()
        finally:
            db.close()

        resp = client.post(
            "/api/v1/applications/analytics/trigger-reminder-digest", headers=auth_headers
        )
        assert resp.json()["users_notified"] == 1

    def test_trigger_does_not_notify_for_distant_interview(
        self, client: TestClient, auth_headers: dict[str, str]
    ):
        app_id = _create(client, auth_headers, "hr_interview").json()["id"]
        far_future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        client.patch(
            f"/api/v1/applications/{app_id}", json={"interview_at": far_future}, headers=auth_headers
        )

        resp = client.post(
            "/api/v1/applications/analytics/trigger-reminder-digest", headers=auth_headers
        )
        assert resp.json()["users_notified"] == 0
