"""Check SMTP access or explicitly send a test email to an operator's address."""
import argparse
import smtplib
import ssl
import sys

from app.core.config import settings
from app.services.email import EmailDeliveryError, _send_email, ensure_email_configured


def main() -> int:
    parser = argparse.ArgumentParser(description="Veyra SMTP bağlantı testi")
    parser.add_argument("--to", help="İsteğe bağlı test alıcısı; verilirse gerçek e-posta gönderilir")
    args = parser.parse_args()
    try:
        ensure_email_configured()
        if args.to:
            _send_email(args.to, "Veyra — E-posta bağlantı testi", "Veyra sistem e-posta gönderimi çalışıyor. Bu ileti bir bağlantı testidir.")
            print("Test e-postası SMTP tarafından kabul edildi. Alıcının gelen kutusunu kontrol edin.")
        else:
            context = ssl.create_default_context()
            if settings.SMTP_USE_SSL:
                connection = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS, context=context)
            else:
                connection = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS)
            with connection as server:
                server.ehlo()
                if settings.SMTP_USE_TLS:
                    server.starttls(context=context)
                    server.ehlo()
                if settings.SMTP_USER:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            print("SMTP bağlantısı ve kimlik doğrulaması başarılı. E-posta gönderilmedi.")
        return 0
    except (EmailDeliveryError, smtplib.SMTPException, OSError, ValueError) as exc:
        # Never print provider replies (which can contain credentials or addresses).
        print(str(exc) if isinstance(exc, EmailDeliveryError) else f"SMTP kontrolü başarısız ({type(exc).__name__}). Sağlayıcı ayarlarını kontrol edin.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
