"""Testlerde paylaşılan örnek veri ve yardımcılar."""

import io

import fitz
from fastapi.testclient import TestClient

from app.agents.resume_schema import (
    EducationEntry,
    ExperienceEntry,
    ParsedResume,
    PersonalInfo,
)

SAMPLE_CV_TEXT = """Arda Yılmaz
arda.yilmaz@example.com | +90 532 123 45 67 | İstanbul

EĞİTİM
İstanbul Teknik Üniversitesi - Bilgisayar Mühendisliği (2019 - 2023) GPA: 3.4/4.0

DENEYİM
Acme Yazılım - Backend Developer (Haziran 2023 - Halen)
Python ve FastAPI ile mikroservis geliştirme, PostgreSQL sorgu optimizasyonu.

PROJELER
CV Agent: Claude API kullanan kariyer asistanı. Teknolojiler: Python, FastAPI, React

YETENEKLER
Python, FastAPI, PostgreSQL, Docker, Git

SERTİFİKALAR
AWS Certified Cloud Practitioner

YABANCI DİL
İngilizce - B2
"""


def make_pdf_bytes(text: str = SAMPLE_CV_TEXT) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    # insert_textbox'ın varsayılan fontu Türkçe karakterleri kodlayamıyor;
    # insert_htmlbox Unicode'u gömülü fontla doğru işler.
    html = "<pre style='font-size:10px'>" + text + "</pre>"
    page.insert_htmlbox(fitz.Rect(40, 40, 555, 800), html)
    data = doc.tobytes()
    doc.close()
    return data


FAKE_PARSED = ParsedResume(
    personal_info=PersonalInfo(
        name="Arda Yılmaz", email="arda.yilmaz@example.com", phone="+90 532 123 45 67"
    ),
    education=[
        EducationEntry(
            school="İstanbul Teknik Üniversitesi",
            department="Bilgisayar Mühendisliği",
            start_date="2019",
            end_date="2023",
            gpa="3.4/4.0",
        )
    ],
    experience=[
        ExperienceEntry(
            company="Acme Yazılım",
            role="Backend Developer",
            start_date="Haziran 2023",
            end_date=None,
            description="Python ve FastAPI ile mikroservis geliştirme.",
        )
    ],
    projects=[],
    skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Git"],
    certificates=["AWS Certified Cloud Practitioner"],
    languages=[],
)


def upload_pdf(client: TestClient, headers: dict[str, str], filename: str = "cv.pdf"):
    return client.post(
        "/api/v1/resumes/upload",
        files={"file": (filename, io.BytesIO(make_pdf_bytes()), "application/pdf")},
        headers=headers,
    )


def register_and_login(client: TestClient, credentials: dict[str, str]) -> str:
    """Kayıt olur, e-posta doğrulamasını (gerçek bir e-posta akışına girmeden,
    doğrudan DB üzerinden) tamamlar ve giriş yapıp erişim token'ı döner.

    Login artık `is_verified=True` şartı koştuğundan, bu akışı kullanan her
    testin ayrıca doğrulamayı simüle etmesi gerekir; bu yardımcı o tekrarı
    tek bir yerde toplar.
    """
    from app.models import User
    from tests.conftest import TestingSessionLocal

    resp = client.post("/api/v1/auth/register", json=credentials)
    assert resp.status_code == 201, resp.text

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == credentials["email"]).one()
        user.is_verified = True
        db.commit()
    finally:
        db.close()

    resp = client.post("/api/v1/auth/login", json=credentials)
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]
