from fastapi.testclient import TestClient

from tests.fixtures import register_and_login


class TestRegister:
    def test_unconfigured_email_does_not_create_an_account(self, client, monkeypatch, user_credentials):
        from app.services.email import EmailDeliveryError

        def unavailable():
            raise EmailDeliveryError("E-posta hizmeti yapılandırılmamış")

        monkeypatch.setattr("app.api.routes.auth.ensure_email_configured", unavailable)
        response = client.post("/api/v1/auth/register", json=user_credentials)
        assert response.status_code == 503
        monkeypatch.setattr("app.api.routes.auth.ensure_email_configured", lambda: None)
        assert client.post("/api/v1/auth/register", json=user_credentials).status_code == 201

    def test_failed_delivery_can_be_retried_without_bypassing_verification(
        self, client, monkeypatch, user_credentials
    ):
        from app.services.email import EmailDeliveryError

        def fail(*args):
            raise EmailDeliveryError("SMTP gönderimi başarısız")

        monkeypatch.setattr("app.api.routes.auth.send_verification_email", fail)
        response = client.post("/api/v1/auth/register", json=user_credentials)
        assert response.status_code == 503
        assert "Hesabın oluşturuldu" in response.json()["detail"]
        assert client.post("/api/v1/auth/login", json=user_credentials).status_code == 403
        captured = {}

        def capture(to_email, url):
            captured["token"] = url.split("token=", 1)[1]

        monkeypatch.setattr("app.api.routes.auth.send_verification_email", capture)
        assert client.post("/api/v1/auth/resend-verification", json={"email": user_credentials["email"]}).status_code == 202
        assert client.post("/api/v1/auth/verify-email", json=captured).status_code == 200
        assert client.post("/api/v1/auth/login", json=user_credentials).status_code == 200

    def test_register_success(self, client: TestClient, user_credentials: dict[str, str]):
        resp = client.post("/api/v1/auth/register", json=user_credentials)
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == user_credentials["email"]
        assert body["is_active"] is True
        assert "id" in body
        assert "password" not in body
        assert "hashed_password" not in body

    def test_register_duplicate_email(self, client: TestClient, user_credentials: dict[str, str]):
        assert client.post("/api/v1/auth/register", json=user_credentials).status_code == 201
        resp = client.post("/api/v1/auth/register", json=user_credentials)
        assert resp.status_code == 409

    def test_register_invalid_email(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/register", json={"email": "gecersiz", "password": "sifre1234"}
        )
        assert resp.status_code == 422

    def test_register_short_password(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/register", json={"email": "a@b.com", "password": "kisa"}
        )
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client: TestClient, user_credentials: dict[str, str]):
        register_and_login(client, user_credentials)  # asserts 201 + 200 internally

    def test_login_blocked_before_email_verification(
        self, client: TestClient, user_credentials: dict[str, str]
    ):
        client.post("/api/v1/auth/register", json=user_credentials)
        resp = client.post("/api/v1/auth/login", json=user_credentials)
        assert resp.status_code == 403

    def test_login_wrong_password(self, client: TestClient, user_credentials: dict[str, str]):
        client.post("/api/v1/auth/register", json=user_credentials)
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": user_credentials["email"], "password": "yanlis-sifre"},
        )
        assert resp.status_code == 401

    def test_login_unknown_email(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/login", json={"email": "yok@example.com", "password": "sifre1234"}
        )
        assert resp.status_code == 401


class TestEmailVerification:
    def _register_and_capture_token(
        self, client: TestClient, monkeypatch, credentials: dict[str, str]
    ) -> str:
        captured = {}

        def fake_send(to_email: str, verify_url: str) -> None:
            captured["token"] = verify_url.rsplit("token=", 1)[1]

        monkeypatch.setattr("app.api.routes.auth.send_verification_email", fake_send)
        resp = client.post("/api/v1/auth/register", json=credentials)
        assert resp.status_code == 201, resp.text
        return captured["token"]

    def test_verify_unlocks_login(
        self, client: TestClient, monkeypatch, user_credentials: dict[str, str]
    ):
        token = self._register_and_capture_token(client, monkeypatch, user_credentials)

        resp = client.post("/api/v1/auth/verify-email", json={"token": token})
        assert resp.status_code == 200

        resp = client.post("/api/v1/auth/login", json=user_credentials)
        assert resp.status_code == 200

    def test_verify_token_is_single_use(
        self, client: TestClient, monkeypatch, user_credentials: dict[str, str]
    ):
        token = self._register_and_capture_token(client, monkeypatch, user_credentials)
        assert client.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 200

        resp = client.post("/api/v1/auth/verify-email", json={"token": token})
        assert resp.status_code == 400

    def test_verify_rejects_garbage_token(self, client: TestClient):
        resp = client.post("/api/v1/auth/verify-email", json={"token": "not-a-real-token"})
        assert resp.status_code == 400

    def test_resend_verification_generic_message_for_unknown_email(self, client: TestClient):
        """Bilinmeyen e-posta da kayıtlı bir e-posta ile AYNI mesajı almalı
        (user enumeration önlemi, request_password_reset ile aynı desen)."""
        resp = client.post(
            "/api/v1/auth/resend-verification", json={"email": "yok@example.com"}
        )
        assert resp.status_code == 202
        generic_message = resp.json()["message"]

        resp2 = client.post(
            "/api/v1/auth/register", json={"email": "bilinen@example.com", "password": "sifre1234"}
        )
        assert resp2.status_code == 201
        resp3 = client.post(
            "/api/v1/auth/resend-verification", json={"email": "bilinen@example.com"}
        )
        assert resp3.json()["message"] == generic_message

    def test_resend_issues_a_working_new_token(
        self, client: TestClient, monkeypatch, user_credentials: dict[str, str]
    ):
        client.post("/api/v1/auth/register", json=user_credentials)

        captured = {}
        monkeypatch.setattr(
            "app.api.routes.auth.send_verification_email",
            lambda to_email, verify_url: captured.setdefault(
                "token", verify_url.rsplit("token=", 1)[1]
            ),
        )
        resp = client.post(
            "/api/v1/auth/resend-verification", json={"email": user_credentials["email"]}
        )
        assert resp.status_code == 202
        assert "token" in captured

        resp = client.post("/api/v1/auth/verify-email", json={"token": captured["token"]})
        assert resp.status_code == 200


class TestPasswordReset:
    def _request_and_capture_token(
        self, client: TestClient, monkeypatch, email: str
    ) -> str:
        captured = {}

        def fake_send(to_email: str, reset_url: str) -> None:
            captured["token"] = reset_url.rsplit("token=", 1)[1]

        monkeypatch.setattr("app.api.routes.auth.send_password_reset_email", fake_send)
        resp = client.post("/api/v1/auth/password-reset/request", json={"email": email})
        assert resp.status_code == 202
        return captured["token"]

    def test_full_reset_flow_changes_password(
        self, client: TestClient, monkeypatch, user_credentials: dict[str, str]
    ):
        register_and_login(client, user_credentials)

        token = self._request_and_capture_token(
            client, monkeypatch, user_credentials["email"]
        )
        resp = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": token, "new_password": "YeniSifre999"},
        )
        assert resp.status_code == 200

        # Eski şifre artık çalışmamalı, yenisi çalışmalı.
        old = client.post("/api/v1/auth/login", json=user_credentials)
        assert old.status_code == 401
        new = client.post(
            "/api/v1/auth/login",
            json={"email": user_credentials["email"], "password": "YeniSifre999"},
        )
        assert new.status_code == 200

    def test_reset_token_is_single_use(
        self, client: TestClient, monkeypatch, user_credentials: dict[str, str]
    ):
        register_and_login(client, user_credentials)
        token = self._request_and_capture_token(
            client, monkeypatch, user_credentials["email"]
        )

        first = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": token, "new_password": "YeniSifre999"},
        )
        assert first.status_code == 200

        second = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": token, "new_password": "BaskaSifre000"},
        )
        assert second.status_code == 400

    def test_reset_rejects_garbage_token(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": "not-a-real-token", "new_password": "YeniSifre999"},
        )
        assert resp.status_code == 400

    def test_request_generic_message_for_unknown_email(self, client: TestClient):
        """Bilinmeyen e-posta da kayıtlı bir e-posta ile AYNI mesajı almalı
        (user enumeration önlemi)."""
        unknown = client.post(
            "/api/v1/auth/password-reset/request", json={"email": "yok@example.com"}
        )
        assert unknown.status_code == 202

        client.post(
            "/api/v1/auth/register",
            json={"email": "bilinen2@example.com", "password": "sifre1234"},
        )
        known = client.post(
            "/api/v1/auth/password-reset/request", json={"email": "bilinen2@example.com"}
        )
        assert known.json()["message"] == unknown.json()["message"]


class TestMe:
    def test_me_success(
        self, client: TestClient, auth_headers: dict[str, str], user_credentials: dict[str, str]
    ):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == user_credentials["email"]

    def test_me_without_token(self, client: TestClient):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token(self, client: TestClient):
        resp = client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer gecersiz.token.degeri"}
        )
        assert resp.status_code == 401
