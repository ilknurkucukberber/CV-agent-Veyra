"""Üç LLM sağlayıcısı (Anthropic, Gemini, Groq) için ortak yapılandırılmış-çıktı katmanı.

Agent modülleri `parse_structured(...)` çağırır; hangi sağlayıcının aktif
olduğuna (bkz. `resolve_provider`) ve o sağlayıcıya özgü tuhaflıklara
(Groq'un şema-zarfı taklidi, dil sızıntısı vb.) bu dosya bakar.
"""

import json
import logging
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Groq'un ücretsiz/on-demand katmanı dakika başına toplam token (TPM) sınırlar
# (ör. 12000 TPM). Tek bir istek prompt + max_tokens toplamıyla bu sınırı
# aşarsa 413/429 döner — bu yüzden max_tokens'ı burada tepede sıkı tutuyoruz.
GROQ_MAX_TOKENS_CAP = 4000

# CJK (Çince/Japonca/Korece) Unicode aralıkları. Uygulama yalnızca Türkçe
# yanıt üretir; açık model zaman zaman bu betiklerden tek bir karakter
# sızdırabiliyor (ör. "container化"). Bunun Türkçe metinde meşru bir
# kullanımı yok, bu yüzden savunma amaçlı olarak temizleniyor.
_STRAY_SCRIPT_PATTERN = re.compile(
    "[一-鿿぀-ヿ가-힣]"
)


def _strip_stray_scripts(value: Any) -> Any:
    if isinstance(value, str):
        cleaned = _STRAY_SCRIPT_PATTERN.sub("", value)
        return re.sub(r" {2,}", " ", cleaned).strip() if cleaned != value else value
    if isinstance(value, list):
        return [_strip_stray_scripts(item) for item in value]
    if isinstance(value, dict):
        return {key: _strip_stray_scripts(item) for key, item in value.items()}
    return value


class LLMError(Exception):
    """Safe, user-facing error for a failed AI request."""


class LLMConfigurationError(LLMError):
    """Missing credentials or invalid provider configuration; do not retry."""


def resolve_provider() -> str:
    if settings.LLM_PROVIDER in ("anthropic", "gemini", "groq"):
        return settings.LLM_PROVIDER
    if settings.LLM_PROVIDER != "auto":
        raise LLMConfigurationError("Yapay zekâ sağlayıcı ayarı geçersiz. Lütfen site yöneticisine bildir.")
    if settings.ANTHROPIC_API_KEY:
        return "anthropic"
    if settings.GEMINI_API_KEY:
        return "gemini"
    if settings.GROQ_API_KEY:
        return "groq"
    raise LLMConfigurationError(
        "Yapay zekâ servisi yapılandırılmamış. CV ayrıştırma ve analiz için site yöneticisinin bir sağlayıcı API anahtarı tanımlaması gerekiyor."
    )


def ensure_configured() -> str:
    provider = resolve_provider()
    key = getattr(settings, f"{provider.upper()}_API_KEY", "").strip()
    if not key or key in {"...", "sk-ant-...", "gsk_..."}:
        raise LLMConfigurationError(
            "Seçilen yapay zekâ sağlayıcısının API anahtarı eksik. Lütfen site yöneticisine bildir."
        )
    return provider


def _placeholder_for(field_schema: dict[str, Any]) -> Any:
    """Bir alanın JSON Schema tanımına göre örnek/iskelet bir değer üretir."""
    field_type = field_schema.get("type")
    if field_type == "array":
        return []
    if field_type == "integer":
        return 0
    if field_type == "number":
        return 0
    if field_type == "boolean":
        return False
    if field_type == "object":
        return {}
    # str | None gibi anyOf alanları (örn. {"anyOf": [{"type": "string"}, {"type": "null"}]})
    any_of = field_schema.get("anyOf")
    if any_of:
        for option in any_of:
            if option.get("type") == "array":
                return []
        return None
    return None


def _flat_skeleton(output_model: type[BaseModel]) -> dict[str, Any]:
    """Modelin DÜZ (nested şema zarfı olmadan) örnek/iskelet halini üretir.

    Ham `model_json_schema()` çıktısını olduğu gibi modele vermek, zayıf/açık
    modellerin (ör. Llama) şemanın kendisini (properties/type/title anahtarlarıyla)
    yanıt sanıp o zarfı birebir taklit etmesine yol açabiliyor. Bunun yerine modele
    doldurması gereken DÜZ örnek objeyi gösteriyoruz.
    """
    schema = output_model.model_json_schema()
    properties = schema.get("properties", {})
    return {name: _placeholder_for(field_schema) for name, field_schema in properties.items()}


def _unwrap_if_schema_envelope(data: Any, expected_keys: set[str]) -> Any:
    """Model, şemayı birebir taklit edip veriyi 'properties' altına sarmışsa düzeltir."""
    if not isinstance(data, dict):
        return data
    if expected_keys & data.keys():
        return data
    nested = data.get("properties")
    if isinstance(nested, dict) and expected_keys & nested.keys():
        return nested
    return data


def parse_structured_groq(
    system: str,
    user_content: str,
    output_model: type[T],
    max_tokens: int = 8000,
) -> T:
    from groq import Groq

    if not settings.GROQ_API_KEY:
        raise LLMConfigurationError("Groq API anahtarı tanımlı değil.")

    client = Groq(api_key=settings.GROQ_API_KEY)
    skeleton = _flat_skeleton(output_model)
    expected_keys = set(skeleton.keys())
    schema_system = (
        f"{system}\n\n"
        "Yanıtını YALNIZCA aşağıdaki DÜZ (flat) örnekle AYNI anahtarlara sahip, "
        "başka hiçbir açıklama, markdown ya da kod bloğu içermeyen geçerli tek bir "
        "JSON nesnesi olarak ver. Bu örnek sadece alan adlarını ve tiplerini "
        "gösterir; değerleri ilan/CV metninden doldur:\n"
        f"{json.dumps(skeleton, ensure_ascii=False)}\n\n"
        "ÇOK ÖNEMLİ: Yanıtını asla 'properties', 'type', 'title' gibi şema "
        "anahtarlarıyla sarmalama. Doğrudan yukarıdaki örnekteki anahtarları "
        "en üst seviyede (top-level) kullan."
    )
    capped_max_tokens = min(max_tokens, GROQ_MAX_TOKENS_CAP)

    messages: list[dict[str, str]] = [
        {"role": "system", "content": schema_system},
        {"role": "user", "content": user_content},
    ]

    last_error: Exception | None = None
    for attempt in range(2):
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            max_tokens=capped_max_tokens,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=messages,
        )
        choice = completion.choices[0]
        if choice.finish_reason == "length":
            raise LLMError("Model yanıtı token limitine takıldı; çıktı eksik olabilir.")

        raw = choice.message.content or ""
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue

        unwrapped = _unwrap_if_schema_envelope(parsed, expected_keys)
        if unwrapped is not parsed:
            logger.warning(
                "Groq yanıtı şema zarfına sarılmıştı; otomatik olarak düzeltildi (model=%s).",
                settings.GROQ_MODEL,
            )

        sanitized = _strip_stray_scripts(unwrapped)

        try:
            return output_model.model_validate(sanitized)
        except ValidationError as exc:
            last_error = exc
            if attempt == 0:
                # İlk deneme başarısızsa modele somut düzeltici geri bildirim verip tekrar dene.
                messages = messages + [
                    {"role": "assistant", "content": raw},
                    {
                        "role": "user",
                        "content": (
                            "Bu yanıt geçersizdi: "
                            f"{exc}. Lütfen SADECE düz JSON nesnesini, yukarıdaki "
                            "örnekteki anahtarlarla birebir aynı şekilde, şema "
                            "zarfı olmadan tekrar üret."
                        ),
                    },
                ]
            continue

    raise LLMError(
        "Model çıktıyı yapılandırılmış biçime dönüştüremedi. Lütfen metni "
        "sadeleştirip tekrar deneyin."
    ) from last_error


def parse_structured_gemini(
    system: str,
    user_content: str,
    output_model: type[T],
    max_tokens: int = 8000,
) -> T:
    """Gemini'nin native şema-kısıtlı JSON çıktısını kullanır.

    Groq'un aksine Gemini, `response_schema` ile modele doğrudan Pydantic
    şemasını verip SDK'nın kendi içinde doğrulamasını sağlıyor — bu yüzden
    Groq yolundaki şema-zarfı taklidi sorunu burada yapısal olarak oluşmaz.
    Yine de açık modellerin CV/ilan metninden dil sızdırma ihtimaline karşı
    aynı savunma katmanını (CJK temizliği) burada da uyguluyoruz.
    """
    from google import genai
    from google.genai import types as genai_types

    if not settings.GEMINI_API_KEY:
        raise LLMConfigurationError("Gemini API anahtarı tanımlı değil.")

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=user_content,
            config=genai_types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=output_model,
                max_output_tokens=max_tokens,
                temperature=0.3,
            ),
        )
    except Exception:
        # The shared caller classifies SDK failures without exposing raw replies.
        raise

    if response.parsed is None:
        raise LLMError(
            "Model çıktıyı yapılandırılmış biçime dönüştüremedi. Lütfen metni "
            "sadeleştirip tekrar deneyin."
        )

    parsed_data = response.parsed.model_dump() if isinstance(response.parsed, BaseModel) else response.parsed
    sanitized = _strip_stray_scripts(parsed_data)
    return output_model.model_validate(sanitized)


def parse_structured(
    system: str,
    user_content: str,
    output_model: type[T],
    max_tokens: int = 8000,
    language: str = "tr",
) -> T:
    # Configuration failures must not enter the retry loop or reach the queue.
    provider = ensure_configured()
    return _parse_with_retry(provider, system, user_content, output_model, max_tokens, language)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(lambda exc: isinstance(exc, LLMError) and not isinstance(exc, LLMConfigurationError)),
    reraise=True,
)
def _parse_with_retry(
    provider: str,
    system: str,
    user_content: str,
    output_model: type[T],
    max_tokens: int = 8000,
    language: str = "tr",
) -> T:
    """Aktif sağlayıcıya (bkz. resolve_provider) göre yapılandırılmış çıktı üretir.

    Her agent'ın ayrı ayrı groq/anthropic dallanması yazmasını önlemek için
    tek giriş noktası. Sağlayıcıya özgü hatalar burada LLMError'a çevrilir;
    çağıran agent kendi hata tipine (ör. ResumeParseError) bu tek noktadan
    sarmalar. Ağ ve API hatalarına karşı tenacity ile otomatik tekrar dener.
    """
    system = f"{system}\n\nIMPORTANT: Produce all generated text and content strictly in {language.upper()} language."

    try:
        if provider == "groq":
            return parse_structured_groq(system, user_content, output_model, max_tokens)
        if provider == "gemini":
            return parse_structured_gemini(system, user_content, output_model, max_tokens)
        return _parse_structured_anthropic(system, user_content, output_model, max_tokens)
    except LLMError:
        raise
    except Exception as exc:
        # Google Gen AI uses .code; Anthropic and Groq use .status_code.
        code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        if code is None:
            code = getattr(getattr(exc, "response", None), "status_code", None)
        logger.error("AI request failed (provider=%s, status=%s, type=%s)", provider, code, type(exc).__name__)
        if code in (401, 403):
            raise LLMConfigurationError("Yapay zekâ hizmetinin API anahtarı geçersiz veya erişim yetkisi yok. Lütfen site yöneticisine bildir.") from exc
        if code == 429:
            raise LLMError("Yapay zekâ hizmetinin kullanım limiti doldu. Biraz sonra tekrar dene; sorun sürerse sağlayıcı kotasını kontrol ettir.") from exc
        if code == 400:
            raise LLMConfigurationError("Yapay zekâ hizmeti isteği geçersiz buldu (400). API anahtarı, model veya çıktı şeması ayarlarının kontrol edilmesi gerekiyor.") from exc
        if code == 404:
            raise LLMConfigurationError("Yapay zekâ hizmeti isteği kabul etmedi. Sağlayıcı ve model ayarlarının kontrol edilmesi gerekiyor.") from exc
        if isinstance(exc, (ValueError, TypeError, AttributeError)):
            raise LLMConfigurationError("Yapay zekâ SDK'sı CV çıktı şemasını veya yanıtını işleyemedi. Site yöneticisinin SDK ve şema uyumluluğunu kontrol etmesi gerekiyor.") from exc
        raise LLMError("Yapay zekâ hizmetine ulaşılamadı. Biraz sonra CV'yi yeniden işlemeyi dene.") from exc


def _parse_structured_anthropic(
    system: str,
    user_content: str,
    output_model: type[T],
    max_tokens: int,
) -> T:
    import anthropic

    if not settings.ANTHROPIC_API_KEY:
        raise LLMConfigurationError("Anthropic API anahtarı tanımlı değil.")

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.parse(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_content}],
        output_format=output_model,
    )

    if response.stop_reason == "refusal":
        raise LLMError("Model isteği reddetti (stop_reason=refusal).")
    if response.stop_reason == "max_tokens":
        raise LLMError("Model yanıtı token limitine takıldı; çıktı eksik olabilir.")
    if response.parsed_output is None:
        raise LLMError("Model çıktısı şemaya uygun ayrıştırılamadı.")

    return response.parsed_output
