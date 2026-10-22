from datetime import datetime

from app.core import llm
from app.schemas.salary import SalaryEstimateResponse

ESTIMATE_SYSTEM_PROMPT = """\
Sen bir insan kaynakları ve ücretlendirme uzmanısın. Kullanıcının girdiği pozisyon, \
şehir ve deneyim seviyesine göre yaklaşık bir maaş aralığı tahmin etmelisin.

KRİTİK KURAL:
- Değerleri güncel ekonomik duruma göre mantıklı bir aralıkta (aylık net maaş) üret.
- Sadece tam sayı olarak range_low, range_mid ve range_high dön.
- "source" alanını "AI Tahmini" olarak ayarla.
- "currency" alanını uygun para birimi (örn: "TRY", "USD", "EUR") yap.
"""

def estimate_salary_with_llm(position: str, city: str, experience_level: str, language: str = "tr") -> SalaryEstimateResponse:
    content = f"Pozisyon: {position}\nŞehir: {city}\nDeneyim Seviyesi: {experience_level}"
    
    result = llm.parse_structured(
        ESTIMATE_SYSTEM_PROMPT,
        content,
        SalaryEstimateResponse,
        max_tokens=2000,
        language=language
    )
    result.source = "AI Tahmini"
    result.source_date = datetime.now().strftime("%Y-%m")
    return result
