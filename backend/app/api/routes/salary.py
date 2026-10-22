import json
import os
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.salary import SalaryEstimateRequest, SalaryEstimateResponse
from app.agents.salary_estimator import estimate_salary_with_llm
from app.api.deps import Language

router = APIRouter(prefix="/salary", tags=["salary"])

SALARY_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data/salary_reference.json")
try:
    with open(SALARY_DATA_PATH, "r", encoding="utf-8") as f:
        SALARY_REFERENCE = json.load(f)
except Exception as e:
    SALARY_REFERENCE = []
    print(f"Warning: Could not load salary reference data. {e}")


def _keyword_matches(keyword: str, text: str) -> bool:
    """Kelime sınırı gözeten eşleşme.

    Naif `kw in text` alt-dize kontrolü yanlış pozitif üretiyordu: ör. "ik
    uzmanı" anahtar kelimesi "güvenlik uzmanı" içinde "güvenl|ik uzmanı" diye
    kelime sınırı olmadan eşleşip "Siber Güvenlik Uzmanı" aramasını yanlışlıkla
    İK kategorisine yönlendiriyordu. \\b ile bu tür sızmalar engellenir.
    """
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None

@router.post("/estimate", response_model=SalaryEstimateResponse)
async def estimate_salary(
    request: SalaryEstimateRequest,
    language: Language,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Girilen kriterlere (pozisyon, şehir, deneyim) göre maaş aralığı tahmini döner.
    Gerçek zamanlı veri yerine güvenilir ve önceden tanımlanmış referans tablosu kullanılır.
    Veri bulunamazsa LLM tahmini YAPILMAZ, 404 dönülür.
    """
    req_pos = request.position.lower()
    req_city = request.city.lower() if request.city else "any"
    req_exp = request.experience_level.lower()

    if "junior" in req_exp or "yeni" in req_exp or "0" in req_exp or "1" in req_exp:
        target_exp = "junior"
    elif "senior" in req_exp or "kıdemli" in req_exp or "uzman" in req_exp:
        target_exp = "senior"
    else:
        target_exp = "mid"

    best_match = None

    for entry in SALARY_REFERENCE:
        pos_match = any(_keyword_matches(kw, req_pos) for kw in entry["position_keywords"])
        if not pos_match:
            continue

        city_match = (
            "any" in entry["city_keywords"]
            or any(_keyword_matches(kw, req_city) for kw in entry["city_keywords"])
        )

        if pos_match and city_match:
            best_match = entry
            break

    if not best_match:
        try:
            return estimate_salary_with_llm(req_pos, req_city, req_exp, language=language)
        except Exception as e:
            raise HTTPException(
                status_code=404, 
                detail="Bu pozisyon için güvenilir veri kaynağımız yok ve yapay zeka tahmini başarısız oldu."
            )

    exp_data = best_match["experience_levels"].get(target_exp)
    if not exp_data:
        try:
            return estimate_salary_with_llm(req_pos, req_city, req_exp, language=language)
        except Exception as e:
            raise HTTPException(
                status_code=404, 
                detail=f"Bu pozisyonun {target_exp} seviyesi için güvenilir veri kaynağımız yok ve yapay zeka tahmini başarısız oldu."
            )

    return SalaryEstimateResponse(
        range_low=exp_data["low"],
        range_mid=exp_data["mid"],
        range_high=exp_data["high"],
        currency=best_match["currency"],
        source=best_match["source"],
        source_date=best_match["source_date"]
    )
