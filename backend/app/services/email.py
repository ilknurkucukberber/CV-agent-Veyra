"""Authenticated SMTP delivery for Veyra transactional email.

Delivery succeeds only when the SMTP server accepts the recipient. Missing
configuration and SMTP errors raise EmailDeliveryError; tokens are never logged.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from html import escape
from urllib.parse import urlsplit

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """SMTP is not configured or did not accept the message."""


def ensure_email_configured() -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise EmailDeliveryError("E-posta gönderim hizmeti henüz yapılandırılmamış. Lütfen site yöneticisine bildirin.")
    if settings.SMTP_USE_SSL == settings.SMTP_USE_TLS:
        raise EmailDeliveryError("E-posta hizmetinin güvenli bağlantı ayarları hatalı. Lütfen site yöneticisine bildirin.")
    if bool(settings.SMTP_USER) != bool(settings.SMTP_PASSWORD):
        raise EmailDeliveryError("E-posta hizmetinin kimlik bilgileri eksik. Lütfen site yöneticisine bildirin.")
    if not 1 <= settings.SMTP_PORT <= 65535 or settings.SMTP_TIMEOUT_SECONDS <= 0:
        raise EmailDeliveryError("E-posta hizmetinin bağlantı ayarları hatalı. Lütfen site yöneticisine bildirin.")
    if any(c in settings.SMTP_FROM_EMAIL for c in "\r\n") or "@" not in settings.SMTP_FROM_EMAIL:
        raise EmailDeliveryError("E-posta hizmetinin gönderici adresi geçersiz.")


def _send_email(to_email: str, subject: str, content: str, html: str | None = None) -> None:
    ensure_email_configured()
    msg = EmailMessage()
    msg.set_content(content)
    if html:
        msg.add_alternative(html, subtype="html")
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.SMTP_FROM_NAME, settings.SMTP_FROM_EMAIL))
    msg["To"] = to_email
    msg["Message-ID"] = make_msgid(domain=settings.SMTP_FROM_EMAIL.rsplit("@", 1)[-1])

    context = ssl.create_default_context()
    try:
        if settings.SMTP_USE_SSL:
            connection = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT,
                                          timeout=settings.SMTP_TIMEOUT_SECONDS, context=context)
        else:
            connection = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT,
                                      timeout=settings.SMTP_TIMEOUT_SECONDS)
        with connection as server:
            server.ehlo()
            if settings.SMTP_USE_TLS:
                server.starttls(context=context)
                server.ehlo()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            refused = server.send_message(msg, from_addr=settings.SMTP_FROM_EMAIL, to_addrs=[to_email])
            if refused:
                raise EmailDeliveryError("E-posta sunucusu alıcı adresini kabul etmedi. Lütfen adresini kontrol edip tekrar dene.")
    except EmailDeliveryError:
        raise
    except (smtplib.SMTPException, OSError) as exc:
        # SMTP replies can contain private addresses. Do not log message bodies,
        # verification URLs, credentials, or raw provider responses.
        logger.error("SMTP delivery failed (%s)", type(exc).__name__)
        raise EmailDeliveryError("E-posta gönderilemedi. Lütfen biraz sonra tekrar dene veya site yöneticisine bildir.") from exc
    logger.info("Transactional email accepted by SMTP server")


def _send_action_email(to_email: str, title: str, copy: str, url: str, action: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise EmailDeliveryError("Site bağlantı adresi hatalı. Lütfen site yöneticisine bildir.")
    body = f"Merhaba,\n\n{copy}\n\n{url}\n\nBu işlemi sen başlatmadıysan bu e-postayı dikkate alma.\n\nVeyra Ekibi"
    html = f"""<!doctype html><html lang="tr"><body style="margin:0;background:#f4f1eb;font-family:Arial,sans-serif;color:#242135">
    <div style="max-width:520px;margin:32px auto;background:#fff;border-radius:18px;padding:36px">
    <p style="font-size:26px;font-weight:bold;color:#7060c9">veyra</p>
    <h1 style="font-size:24px">{escape(title)}</h1><p style="line-height:1.7">{escape(copy)}</p>
    <p style="margin:28px 0"><a href="{escape(url, quote=True)}" style="background:#7060c9;color:white;padding:14px 22px;border-radius:10px;text-decoration:none">{escape(action)}</a></p>
    <p style="font-size:12px;line-height:1.7;color:#666">Düğme çalışmıyorsa bu bağlantıyı tarayıcına kopyala:<br><a href="{escape(url, quote=True)}" style="word-break:break-all">{escape(url)}</a></p>
    <p style="font-size:12px;color:#666">Bu işlemi sen başlatmadıysan bu e-postayı dikkate alma.</p>
    </div></body></html>"""
    _send_email(to_email, f"Veyra — {title}", body, html)


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    _send_action_email(to_email, "Şifreni sıfırla", "Yeni şifreni belirlemek için aşağıdaki bağlantıyı kullan. Bağlantı tek kullanımlıktır.", reset_url, "Şifremi sıfırla")


def send_verification_email(to_email: str, verify_url: str) -> None:
    _send_action_email(to_email, "E-posta adresini doğrula", "Veyra'ya hoş geldin. Hesabını etkinleştirip kariyer alanına giriş yapmak için e-posta adresini doğrula. Bağlantı tek kullanımlıktır.", verify_url, "E-posta adresimi doğrula")


def send_reminder_digest(
    to_email: str,
    upcoming_interviews: list[dict],
    stale_applications: list[dict],
) -> None:
    subject = "Veyra - Kariyer Hatırlatmaları"
    
    lines = ["Merhaba, kariyer yolculuğun için bazı önemli hatırlatmalarımız var:\n"]
    if upcoming_interviews:
        lines.append("📌 Yaklaşan Görüşmeler:")
        for item in upcoming_interviews:
            lines.append(f"  • {item['position']} @ {item['company']} — {item['interview_at']}")
        lines.append("")
        
    if stale_applications:
        lines.append("⏳ Bekleyen Başvurular:")
        for item in stale_applications:
            lines.append(
                f"  • {item['position']} @ {item['company']} — "
                f"{item['days_since_update']} gündür güncellenmedi ({item['status']})"
            )
        lines.append("")
        
    lines.append("\nİyi çalışmalar,\nVeyra Ekibi")
    
    _send_email(to_email, subject, "\n".join(lines))
