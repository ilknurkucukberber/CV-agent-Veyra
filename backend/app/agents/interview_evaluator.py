import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from app.core import llm

logger = logging.getLogger(__name__)


class AnswerFeedback(BaseModel):
    too_general: bool
    missing_technical_detail: bool
    missing_position_connection: bool
    structure_notes: str


class AnswerEvaluation(BaseModel):
    feedback: AnswerFeedback
    suggested_improved_answer: str
    follow_up_question: str | None = None


class InterviewEvaluationError(Exception):
    """Cevap değerlendirilemediğinde fırlatılır."""


SYSTEM_PROMPT = """\
Sen bir mülakat hazırlık koçusun. Adayın bir mülakat sorusuna verdiği cevabı \
değerlendirip yapıcı geri bildirim verirsin.

KRİTİK KURAL: Kullanıcının cevabından kişilik, dürüstlük, güvenilirlik veya \
işe uygunluk hakkında sonuç çıkarma. Sadece cevabın yapısı, netliği, teknik \
detay içerip içermediği ve STAR uyumu gibi gözlemlenebilir unsurları \
değerlendir. "Bu aday deneyimsiz görünüyor", "samimi değil", "bu pozisyona \
uygun değil" gibi kişiye dönük yargılar YASAK — yorumun daima metne dönük olsun.

suggested_improved_answer kuralı (çok önemli):
- YALNIZCA kullanıcının cevabında geçen bilgileri kullan. Yeni proje, yeni \
teknoloji, yeni görev veya yeni sayısal sonuç EKLEME.
- Kullanıcının söylemediği bir metrik uydurma ("%40 hızlandırdım" gibi). \
Cevapta sayı yoksa geliştirilmiş cevapta da sayı olmasın; bunun yerine \
structure_notes içinde "buraya ölçülebilir bir sonuç ekleyebilirsiniz" \
biçiminde eksiği belirt.
- Görevin yeniden yazmak değil, aynı içeriği daha net ve yapılandırılmış \
biçimde ifade etmek. Cevap STAR'a uygunsa Durum-Görev-Eylem-Sonuç akışını \
belirginleştir.
- Kullanıcı hiç içerik vermediyse (çok kısa/boş cevap), uydurma bir cevap \
yazma; bunun yerine cevabın hangi bileşenlerle genişletilmesi gerektiğini \
şablon biçiminde göster ve köşeli parantezle yer tutucu kullan \
(ör. "[hangi projede olduğunu yazın]").

feedback alanları:
- too_general: cevap somut örnek/olay içermiyorsa true.
- missing_technical_detail: teknik bir soruda araç/yaklaşım/karar detayı \
yoksa true.
- missing_position_connection: cevap hedef pozisyonla veya sorunun amacıyla \
ilişkilendirilmemişse true.
- structure_notes: cevabın yapısına dair somut, uygulanabilir notlar. \
Nazik ve yapıcı bir dil kullan; ne eksik ve nasıl tamamlanır onu söyle.

follow_up_question: gerçek bir mülakatta bu cevabın ardından gelmesi muhtemel \
tek bir takip sorusu. Anlamlı bir takip sorusu yoksa null.
Tüm metinleri Türkçe yaz."""

# Kişiye dönük yargı içeren ifadeler — çıktıda tespit edilirse loglanır
JUDGMENT_PATTERNS = [
    r"dürüst değil",
    r"samimi değil",
    r"güvenilir değil",
    r"güvenilmez",
    r"uygun değil(siniz)?",
    r"yetersiz bir aday",
    r"işe alınmaz",
    r"kişiliğ",
]

NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def find_invented_numbers(user_answer: str, improved_answer: str) -> list[str]:
    """Geliştirilmiş cevapta olup kullanıcının cevabında olmayan sayıları döner.

    Uydurma metrik ("%30 azalttım") en sık görülen halüsinasyon biçimi olduğu
    için ayrıca denetlenir.
    """
    source = set(NUMBER_RE.findall(user_answer))
    return [n for n in NUMBER_RE.findall(improved_answer) if n not in source]


def find_judgmental_language(text: str) -> list[str]:
    lowered = text.lower()
    return [p for p in JUDGMENT_PATTERNS if re.search(p, lowered)]


def evaluate_answer(
    question: str,
    user_answer: str,
    star_applicable: bool,
    session_type: str,
    job_title: str | None = None,
    job_requirements: dict[str, Any] | None = None,
    language: str = "tr",
) -> AnswerEvaluation:
    context = [
        f"Görüşme türü: {session_type}",
        f"STAR formatı bekleniyor mu: {'evet' if star_applicable else 'hayır'}",
    ]
    if job_title:
        context.append(f"Hedef pozisyon: {job_title}")

    user_content = (
        "\n".join(context)
        + f"\n\n<soru>\n{question}\n</soru>"
        + f"\n\n<adayin_cevabi>\n{user_answer}\n</adayin_cevabi>"
    )

    try:
        result = llm.parse_structured(
            SYSTEM_PROMPT,
            user_content,
            AnswerEvaluation,
            max_tokens=8000,
            language=language
        )
    except llm.LLMError as exc:
        raise InterviewEvaluationError(str(exc)) from exc

    invented = find_invented_numbers(user_answer, result.suggested_improved_answer)
    if invented:
        logger.warning(
            "Geliştirilmiş cevapta kaynakta olmayan sayı(lar) tespit edildi: %s", invented
        )
    judgmental = find_judgmental_language(result.feedback.structure_notes)
    if judgmental:
        logger.warning("Geri bildirimde kişiye dönük ifade tespit edildi: %s", judgmental)

    return result
