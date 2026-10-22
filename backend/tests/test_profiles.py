from fastapi.testclient import TestClient

PROFILE_PAYLOAD = {
    "education_level": "Lisans",
    "department": "Bilgisayar Mühendisliği",
    "university": "İTÜ",
    "graduation_year": 2024,
    "work_experience": [{"company": "Acme", "role": "Backend Developer", "years": 1}],
    "internship_experience": [{"company": "Beta", "role": "Intern", "months": 3}],
    "technical_skills": ["Python", "FastAPI", "PostgreSQL"],
    "certificates": ["AWS Cloud Practitioner"],
    "projects": [{"name": "CV Agent", "description": "Kariyer asistanı"}],
    "english_level": "B2",
    "target_city": "İstanbul",
    "work_mode_preference": "hybrid",
    "career_goal": "Senior backend developer olmak",
}


class TestCreateProfile:
    def test_create_profile_success(self, client: TestClient, auth_headers: dict[str, str]):
        resp = client.post("/api/v1/profiles", json=PROFILE_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["university"] == "İTÜ"
        assert body["work_mode_preference"] == "hybrid"
        assert body["technical_skills"] == ["Python", "FastAPI", "PostgreSQL"]
        assert "user_id" in body

    def test_create_profile_requires_auth(self, client: TestClient):
        resp = client.post("/api/v1/profiles", json=PROFILE_PAYLOAD)
        assert resp.status_code == 401

    def test_create_profile_duplicate(self, client: TestClient, auth_headers: dict[str, str]):
        assert (
            client.post("/api/v1/profiles", json=PROFILE_PAYLOAD, headers=auth_headers).status_code
            == 201
        )
        resp = client.post("/api/v1/profiles", json=PROFILE_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 409

    def test_create_profile_invalid_graduation_year(
        self, client: TestClient, auth_headers: dict[str, str]
    ):
        payload = {**PROFILE_PAYLOAD, "graduation_year": 1800}
        resp = client.post("/api/v1/profiles", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_profile_invalid_work_mode(
        self, client: TestClient, auth_headers: dict[str, str]
    ):
        payload = {**PROFILE_PAYLOAD, "work_mode_preference": "uzaydan"}
        resp = client.post("/api/v1/profiles", json=payload, headers=auth_headers)
        assert resp.status_code == 422


class TestGetProfile:
    def test_get_my_profile(self, client: TestClient, auth_headers: dict[str, str]):
        client.post("/api/v1/profiles", json=PROFILE_PAYLOAD, headers=auth_headers)
        resp = client.get("/api/v1/profiles/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["department"] == "Bilgisayar Mühendisliği"

    def test_get_my_profile_not_found(self, client: TestClient, auth_headers: dict[str, str]):
        resp = client.get("/api/v1/profiles/me", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_my_profile_requires_auth(self, client: TestClient):
        resp = client.get("/api/v1/profiles/me")
        assert resp.status_code == 401


class TestUpdateProfile:
    def test_update_profile_success(self, client: TestClient, auth_headers: dict[str, str]):
        client.post("/api/v1/profiles", json=PROFILE_PAYLOAD, headers=auth_headers)
        resp = client.patch(
            "/api/v1/profiles/me",
            json={"target_city": "Ankara", "work_mode_preference": "remote"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["target_city"] == "Ankara"
        assert body["work_mode_preference"] == "remote"
        # Gönderilmeyen alanlar değişmemeli
        assert body["university"] == "İTÜ"

    def test_update_profile_not_found(self, client: TestClient, auth_headers: dict[str, str]):
        resp = client.patch(
            "/api/v1/profiles/me", json={"target_city": "Ankara"}, headers=auth_headers
        )
        assert resp.status_code == 404

    def test_update_profile_invalid_year(self, client: TestClient, auth_headers: dict[str, str]):
        client.post("/api/v1/profiles", json=PROFILE_PAYLOAD, headers=auth_headers)
        resp = client.patch(
            "/api/v1/profiles/me", json={"graduation_year": 3000}, headers=auth_headers
        )
        assert resp.status_code == 422

    def test_update_profile_requires_auth(self, client: TestClient):
        resp = client.patch("/api/v1/profiles/me", json={"target_city": "Ankara"})
        assert resp.status_code == 401
