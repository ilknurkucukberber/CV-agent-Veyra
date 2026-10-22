import enum

from pydantic import BaseModel, Field


class SessionType(str, enum.Enum):
    HR = "hr"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"


class QuestionSource(str, enum.Enum):
    GENERAL = "general"
    CV_SPECIFIC = "cv_specific"
    JOB_SPECIFIC = "job_specific"


class InterviewQuestion(BaseModel):
    question: str
    category: str
    source: QuestionSource
    star_applicable: bool


class InterviewQuestionSet(BaseModel):
    questions: list[InterviewQuestion] = Field(default_factory=list)


# Her görüşme türü için sabit soru havuzu. LLM bunları hafifçe çeşitlendirir
# (yeniden ifade eder), böylece çıktı hem tutarlı hem tekdüze olmayan olur.
QUESTION_POOL: dict[SessionType, list[tuple[str, str]]] = {
    SessionType.HR: [
        ("Kendinizden ve kariyer yolculuğunuzdan kısaca bahseder misiniz?", "Tanışma"),
        ("Bu pozisyona neden başvurdunuz?", "Motivasyon"),
        ("Şirketimiz hakkında neler biliyorsunuz?", "Şirket bilgisi"),
        ("Mevcut işinizden ayrılma nedeniniz nedir?", "Kariyer geçişi"),
        ("Ücret beklentiniz nedir?", "Beklentiler"),
        ("Önümüzdeki 3-5 yıl içinde kendinizi nerede görüyorsunuz?", "Kariyer hedefi"),
        ("Ne zaman işe başlayabilirsiniz?", "Uygunluk"),
        ("Uzaktan/hibrit/ofis çalışma tercihiniz nedir?", "Çalışma düzeni"),
    ],
    SessionType.TECHNICAL: [
        ("Üzerinde çalıştığınız bir sistemin mimarisini anlatır mısınız?", "Sistem tasarımı"),
        ("Karmaşık bir hatayı nasıl teşhis edip çözersiniz? Sürecinizi anlatın.", "Hata ayıklama"),
        ("Kod kalitesini nasıl ölçer ve korursunuz?", "Kod kalitesi"),
        ("Test stratejinizi nasıl kurgularsınız?", "Test"),
        ("Bir performans darboğazını nasıl tespit edip giderirsiniz?", "Performans"),
        ("Veritabanı şeması tasarlarken nelere dikkat edersiniz?", "Veri modelleme"),
        ("Yeni bir teknolojiyi öğrenme yaklaşımınız nasıl?", "Öğrenme"),
        ("Kod incelemesinde neye odaklanırsınız?", "Kod inceleme"),
    ],
    SessionType.BEHAVIORAL: [
        ("Bir ekip arkadaşınızla anlaşmazlık yaşadığınız bir durumu anlatın.", "Çatışma yönetimi"),
        ("Başarısız olduğunuz bir projeyi ve bundan çıkardığınız dersi anlatın.", "Başarısızlıktan öğrenme"),
        ("Sıkı bir teslim tarihi baskısı altında çalıştığınız bir örneği anlatın.", "Baskı altında çalışma"),
        ("İnisiyatif alarak bir sorunu çözdüğünüz bir durumu anlatın.", "İnisiyatif"),
        ("Olumsuz bir geri bildirim aldığınız ve buna nasıl yanıt verdiğinizi anlatın.", "Geri bildirim"),
        ("Öncelikleri çakışan işleri yönetmek zorunda kaldığınız bir zamanı anlatın.", "Önceliklendirme"),
        ("Bir başkasına teknik bir konuyu anlatmak zorunda kaldığınız bir örneği paylaşın.", "İletişim"),
        ("Fikrinizi savunduğunuz ama sonunda ikna olduğunuz bir durumu anlatın.", "Esneklik"),
    ],
}

POOL_SAMPLE_SIZE = 5
