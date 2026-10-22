from app.agents.resume_schema import ParsedResume
from app.core import llm

SYSTEM_PROMPT = """\
Sen bir CV ayrıştırma asistanısın. Sana verilen ham CV metnini istenen JSON \
şemasına dönüştürürsün.

KRİTİK KURAL: CV'de açıkça belirtilmeyen hiçbir bilgiyi çıkarma veya uydurma. \
Emin olmadığın alanları null bırak. Listelerde yalnızca metinde açıkça geçen \
öğeler bulunmalıdır; hiçbir alanı tahminle doldurma.

Tarihleri CV'de yazıldığı biçime sadık kalarak aktar (ör. "2021", "Mart 2022", \
"2020 - Halen"). Metinde hiç bulunmayan bölümler için boş liste dön."""


class ResumeParseError(Exception):
    """Claude çağrısı başarısız olduğunda veya reddedildiğinde fırlatılır."""


def parse_resume_text(raw_text: str, language: str = "tr") -> ParsedResume:
    user_content = (
        "Aşağıdaki CV metnini yapılandırılmış veriye dönüştür:\n\n"
        f"<cv_metni>\n{raw_text}\n</cv_metni>"
    )

    try:
        return llm.parse_structured(
            SYSTEM_PROMPT, 
            user_content, 
            ParsedResume,
            max_tokens=12000,
            language=language
        )
    except llm.LLMError as exc:
        raise ResumeParseError(str(exc)) from exc
