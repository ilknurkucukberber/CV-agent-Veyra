"""Provider failures must be actionable and must never surface RetryError."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

from pydantic import BaseModel
from tenacity import wait_none


class Result(BaseModel):
    ok: bool


class LLMErrorTests(unittest.TestCase):
    def setUp(self):
        self.settings = types.SimpleNamespace(
            LLM_PROVIDER="auto", ANTHROPIC_API_KEY="", GEMINI_API_KEY="", GROQ_API_KEY="",
        )
        config = types.ModuleType("app.core.config")
        config.settings = self.settings
        path = Path(__file__).resolve().parents[1] / "app/core/llm.py"
        spec = importlib.util.spec_from_file_location("veyra_llm_unit", path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"app.core.config": config}):
            spec.loader.exec_module(self.module)
        self.module._parse_with_retry.retry.wait = wait_none()

    def call(self):
        return self.module.parse_structured("system", "CV text", Result)

    def test_missing_keys_are_rejected_before_a_provider_request(self):
        with patch.object(self.module, "parse_structured_groq") as provider:
            with self.assertRaises(self.module.LLMConfigurationError) as error:
                self.call()
            provider.assert_not_called()
        self.assertIn("yapılandırılmamış", str(error.exception))

    def test_explicit_provider_requires_its_own_key(self):
        self.settings.LLM_PROVIDER = "gemini"
        self.settings.GROQ_API_KEY = "test-key"
        with self.assertRaises(self.module.LLMConfigurationError):
            self.call()

    def test_auto_provider_selection_uses_available_key(self):
        self.settings.GEMINI_API_KEY = "test-key"
        self.assertEqual(self.module.ensure_configured(), "gemini")

    def test_invalid_provider_is_not_silently_changed(self):
        self.settings.LLM_PROVIDER = "invalid"
        with self.assertRaises(self.module.LLMConfigurationError):
            self.module.ensure_configured()

    def test_exhausted_transient_failure_preserves_original_llm_error(self):
        self.settings.GROQ_API_KEY = "test-key"
        failure = self.module.LLMError("Geçici servis hatası")
        with patch.object(self.module, "parse_structured_groq", side_effect=failure) as provider:
            with self.assertRaises(self.module.LLMError) as error:
                self.call()
            self.assertIs(error.exception, failure)
            self.assertEqual(provider.call_count, 3)
            self.assertNotIn("RetryError", str(error.exception))

    def test_authentication_failure_is_safe_and_is_not_retried(self):
        self.settings.GROQ_API_KEY = "test-key"
        failure = RuntimeError("SECRET and private CV text")
        failure.status_code = 401
        with patch.object(self.module, "parse_structured_groq", side_effect=failure) as provider:
            with self.assertRaises(self.module.LLMConfigurationError) as error:
                self.call()
            self.assertEqual(provider.call_count, 1)
        self.assertNotIn("SECRET", str(error.exception))
        self.assertIn("geçersiz", str(error.exception))

    def test_quota_failure_has_clear_message(self):
        self.settings.GROQ_API_KEY = "test-key"
        failure = RuntimeError("provider raw response")
        failure.status_code = 429
        with patch.object(self.module, "parse_structured_groq", side_effect=failure) as provider:
            with self.assertRaises(self.module.LLMError) as error:
                self.call()
            self.assertEqual(provider.call_count, 3)
        self.assertIn("limit", str(error.exception))
        self.assertNotIn("raw response", str(error.exception))

    def test_success_is_returned_without_retry(self):
        self.settings.GROQ_API_KEY = "test-key"
        expected = Result(ok=True)
        with patch.object(self.module, "parse_structured_groq", return_value=expected) as provider:
            self.assertIs(self.call(), expected)
            self.assertEqual(provider.call_count, 1)

    def test_google_code_field_is_used_for_auth_failure(self):
        self.settings.GEMINI_API_KEY = "test-key"
        failure = RuntimeError("private provider response")
        failure.code = 401
        with patch.object(self.module, "parse_structured_gemini", side_effect=failure) as provider:
            with self.assertRaises(self.module.LLMConfigurationError) as error:
                self.call()
            self.assertEqual(provider.call_count, 1)
        self.assertIn("geçersiz", str(error.exception))

    def test_google_quota_code_is_not_reported_as_network_failure(self):
        self.settings.GEMINI_API_KEY = "test-key"
        failure = RuntimeError("private provider response")
        failure.code = 429
        with patch.object(self.module, "parse_structured_gemini", side_effect=failure):
            with self.assertRaises(self.module.LLMError) as error:
                self.call()
        self.assertIn("limit", str(error.exception))

    def test_unavailable_google_model_is_actionable_and_not_retried(self):
        self.settings.GEMINI_API_KEY = "test-key"
        failure = RuntimeError("private CV text and provider response")
        failure.code = 404
        with patch.object(self.module, "parse_structured_gemini", side_effect=failure) as provider:
            with self.assertRaises(self.module.LLMConfigurationError) as error:
                self.call()
            self.assertEqual(provider.call_count, 1)
        self.assertIn("model", str(error.exception))
        self.assertNotIn("private CV", str(error.exception))

    def test_local_schema_error_is_not_retried_as_network_error(self):
        self.settings.GEMINI_API_KEY = "test-key"
        with patch.object(self.module, "parse_structured_gemini", side_effect=ValueError("private schema input")) as provider:
            with self.assertRaises(self.module.LLMConfigurationError) as error:
                self.call()
            self.assertEqual(provider.call_count, 1)
        self.assertIn("şema", str(error.exception))
        self.assertNotIn("private schema input", str(error.exception))


if __name__ == "__main__":
    unittest.main()
