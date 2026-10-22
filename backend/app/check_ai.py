"""Diagnose the actual CV parsing schema using fictional input only."""
import argparse
import re
from importlib.metadata import version, PackageNotFoundError

from app.agents.resume_schema import ParsedResume
from app.core import llm
from app.core.config import settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Veyra yapay zekâ bağlantı kontrolü")
    parser.add_argument("--test", action="store_true", help="Kurgusal CV ile gerçek bir API isteği yap")
    args = parser.parse_args()
    try:
        provider = llm.ensure_configured()
        print(f"Sağlayıcı: {provider}")
        print(f"Model: {getattr(settings, provider.upper() + '_MODEL', '')}")
        package = {"gemini": "google-genai", "groq": "groq", "anthropic": "anthropic"}[provider]
        try:
            print(f"SDK: {package} {version(package)}")
        except PackageNotFoundError:
            print(f"SDK kurulu değil: {package}")
            return 1
        if not args.test:
            print("Anahtar tanımlı. Gerçek API isteği yapılmadı; bağlantı testi için --test kullanın.")
            return 0
        result = llm.parse_structured(
            "Extract only facts stated in the CV. Return empty lists for absent sections.",
            "Deniz Test\ndeniz.test@example.com\nSkills: Python, FastAPI\nEnglish: B1",
            ParsedResume,
            max_tokens=2048,
        )
        if not result.personal_info.email:
            print("API yanıt verdi ancak test CV'sinin e-posta alanını çıkarmadı.")
            return 1
        print("Başarılı: gerçek API bağlantısı ve CV ayrıştırma şeması doğrulandı.")
        return 0
    except llm.LLMError as exc:
        print(f"Başarısız: {exc}")
        cause = exc.__cause__
        if cause:
            code = getattr(cause, "status_code", None) or getattr(cause, "code", None)
            print(f"Teknik hata türü: {type(cause).__name__}; HTTP kodu: {code or 'yok'}")
            # This command sends fictional data only. Redact credentials before
            # showing the provider's diagnostic (needed for schema/auth issues).
            detail = str(cause)
            for name in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY"):
                secret = getattr(settings, name, "")
                if secret:
                    detail = detail.replace(secret, "[gizlendi]")
            detail = re.sub(r"(?i)([?&]key=)[^&\s]+", r"\1[gizlendi]", detail)
            detail = re.sub(r"(?i)(Bearer\s+)[^\s]+", r"\1[gizlendi]", detail)
            print(f"Sağlayıcı ayrıntısı: {detail[:1200]}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
