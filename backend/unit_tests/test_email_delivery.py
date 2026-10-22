"""SMTP unit tests: no network, account, or database is required."""
import importlib.util
from pathlib import Path
import smtplib
import ssl
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class EmailDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.settings = types.SimpleNamespace(
            SMTP_HOST="smtp.example.org", SMTP_PORT=587,
            SMTP_USER="smtp-user", SMTP_PASSWORD="test-secret",
            SMTP_FROM_EMAIL="noreply@example.org", SMTP_FROM_NAME="Veyra",
            SMTP_USE_SSL=False, SMTP_USE_TLS=True, SMTP_TIMEOUT_SECONDS=15,
        )
        config = types.ModuleType("app.core.config")
        config.settings = self.settings
        path = Path(__file__).resolve().parents[1] / "app/services/email.py"
        spec = importlib.util.spec_from_file_location("veyra_email_unit", path)
        self.service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"app.core.config": config}):
            spec.loader.exec_module(self.service)
        self.smtp = patch.object(self.service.smtplib, "SMTP")
        self.ssl_smtp = patch.object(self.service.smtplib, "SMTP_SSL")
        self.factory = self.smtp.start()
        self.ssl_factory = self.ssl_smtp.start()
        self.addCleanup(self.smtp.stop)
        self.addCleanup(self.ssl_smtp.stop)
        self.server = self.factory.return_value.__enter__.return_value
        self.server.send_message.return_value = {}

    def send(self):
        self.service.send_verification_email("recipient@example.net", "https://site.example.org/verify-email?token=test-token")

    def test_starttls_authenticates_and_sends_branded_multipart_email(self):
        self.send()
        self.factory.assert_called_once_with("smtp.example.org", 587, timeout=15)
        self.server.starttls.assert_called_once()
        context = self.server.starttls.call_args.kwargs["context"]
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.server.login.assert_called_once_with("smtp-user", "test-secret")
        msg = self.server.send_message.call_args.args[0]
        self.assertIn("Veyra", msg["From"])
        self.assertEqual(msg["To"], "recipient@example.net")
        self.assertIn("test-token", msg.get_body(preferencelist=("plain",)).get_content())
        self.assertIn("E-posta adresimi doğrula", msg.get_body(preferencelist=("html",)).get_content())
        self.ssl_factory.assert_not_called()

    def test_implicit_tls_uses_ssl_without_starttls(self):
        self.settings.SMTP_PORT = 465
        self.settings.SMTP_USE_SSL = True
        self.settings.SMTP_USE_TLS = False
        server = self.ssl_factory.return_value.__enter__.return_value
        server.send_message.return_value = {}
        self.send()
        self.factory.assert_not_called()
        self.ssl_factory.assert_called_once()
        server.starttls.assert_not_called()
        self.assertTrue(self.ssl_factory.call_args.kwargs["context"].check_hostname)

    def test_missing_configuration_fails_instead_of_logging_a_token(self):
        self.settings.SMTP_HOST = ""
        with self.assertRaises(self.service.EmailDeliveryError):
            self.send()
        self.factory.assert_not_called()

    def test_missing_sender_fails_before_connecting(self):
        self.settings.SMTP_FROM_EMAIL = ""
        with self.assertRaises(self.service.EmailDeliveryError):
            self.send()
        self.factory.assert_not_called()

    def test_partial_credentials_fail(self):
        self.settings.SMTP_PASSWORD = ""
        with self.assertRaises(self.service.EmailDeliveryError):
            self.send()
        self.factory.assert_not_called()

    def test_insecure_or_conflicting_transport_modes_fail(self):
        for enabled in (False, True):
            self.settings.SMTP_USE_TLS = enabled
            self.settings.SMTP_USE_SSL = enabled
            with self.assertRaises(self.service.EmailDeliveryError):
                self.send()
        self.factory.assert_not_called()

    def test_authentication_failure_is_reported_without_leaking_secrets(self):
        self.server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"test-secret recipient@example.net test-token")
        with self.assertLogs(self.service.logger, level="ERROR") as captured:
            with self.assertRaises(self.service.EmailDeliveryError) as error:
                self.send()
        self.assertNotIn("test-secret", str(error.exception))
        self.assertNotIn("test-token", " ".join(captured.output))
        self.assertNotIn("recipient@example.net", " ".join(captured.output))
        self.server.send_message.assert_not_called()

    def test_connection_timeout_is_reported(self):
        self.factory.side_effect = TimeoutError("timed out")
        with self.assertRaises(self.service.EmailDeliveryError):
            self.send()

    def test_recipient_refusal_is_not_success(self):
        self.server.send_message.return_value = {"recipient@example.net": (550, b"Rejected")}
        with self.assertRaises(self.service.EmailDeliveryError):
            self.send()

    def test_invalid_link_does_not_send(self):
        with self.assertRaises(self.service.EmailDeliveryError):
            self.service.send_verification_email("recipient@example.net", "javascript:alert(1)")
        self.factory.assert_not_called()

    def test_password_reset_contains_correct_action_and_link(self):
        self.service.send_password_reset_email("recipient@example.net", "https://site.example.org/reset-password?token=reset-token")
        msg = self.server.send_message.call_args.args[0]
        self.assertIn("reset-token", msg.get_body(preferencelist=("plain",)).get_content())
        self.assertIn("Şifremi sıfırla", msg.get_body(preferencelist=("html",)).get_content())


if __name__ == "__main__":
    unittest.main()
