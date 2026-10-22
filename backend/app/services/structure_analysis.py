import re
import unicodedata
from typing import Any

from app.services.extraction import ExtractionResult


def _normalize(text: str) -> str:
    """Aksan/diakritikleri atarak küçük harfe çevirir.

    Türkçe 'İ'.lower() -> 'i̇' (combining dot) ürettiği için düz lower() ile
    'EĞİTİM' içinde 'eğitim' aranamaz; NFKD + combining karakter temizliği
    bunu çözer ('EĞİTİM' -> 'egitim').
    """
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{8,}\d)")

# Türkçe + İngilizce yaygın CV bölüm başlıkları
SECTION_KEYWORDS: dict[str, list[str]] = {
    "education": ["eğitim", "egitim", "education", "akademik"],
    "experience": ["deneyim", "tecrübe", "tecrube", "experience", "work history", "iş geçmişi"],
    "skills": ["yetenek", "beceri", "skills", "teknoloji", "technologies"],
    "projects": ["proje", "projects"],
    "languages": ["yabancı dil", "diller", "languages"],
    "certificates": ["sertifika", "certificates", "certifications"],
}

MAX_RECOMMENDED_PAGES = 2


def analyze_structure(extraction: ExtractionResult) -> dict[str, Any]:
    """CV'nin yapısal kalitesini heuristiklerle değerlendirir."""
    text = extraction.text
    normalized = _normalize(text)

    detected = [
        section
        for section, keywords in SECTION_KEYWORDS.items()
        if any(_normalize(kw) in normalized for kw in keywords)
    ]
    missing = [s for s in SECTION_KEYWORDS if s not in detected]

    has_email = bool(EMAIL_RE.search(text))
    has_phone = bool(PHONE_RE.search(text))

    warnings: list[str] = []
    if not has_email:
        warnings.append("İletişim için e-posta adresi bulunamadı.")
    if not has_phone:
        warnings.append("Telefon numarası bulunamadı.")
    if extraction.page_count and extraction.page_count > MAX_RECOMMENDED_PAGES:
        warnings.append(
            f"CV {extraction.page_count} sayfa; {MAX_RECOMMENDED_PAGES} sayfayı aşan CV'ler "
            "işe alım uzmanları tarafından tam okunmayabilir."
        )
    if extraction.table_count > 0:
        warnings.append(
            f"{extraction.table_count} tablo tespit edildi; tablolar ATS sistemlerinde "
            "yanlış ayrıştırılabilir."
        )
    if extraction.multi_column_pages:
        pages = ", ".join(map(str, extraction.multi_column_pages))
        warnings.append(
            f"Çok kolonlu düzen olasılığı (sayfa: {pages}); kolonlu düzenler ATS "
            "sistemlerini zorlayabilir."
        )
    if len(text) < 300:
        warnings.append("Çıkarılan metin çok kısa; dosya taranmış görüntü olabilir.")
    for section in ("education", "experience"):
        if section not in detected:
            warnings.append(f"'{section}' bölümüne ait bir başlık tespit edilemedi.")

    return {
        "page_count": extraction.page_count,
        "too_long": bool(
            extraction.page_count and extraction.page_count > MAX_RECOMMENDED_PAGES
        ),
        "has_email": has_email,
        "has_phone": has_phone,
        "detected_sections": detected,
        "missing_sections": missing,
        "table_count": extraction.table_count,
        "multi_column_pages": extraction.multi_column_pages,
        "character_count": len(text),
        "ats_warnings": warnings,
    }
