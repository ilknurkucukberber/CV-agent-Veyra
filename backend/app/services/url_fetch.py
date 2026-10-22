import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from app.core.config import settings

MAX_REDIRECTS = 3
SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}
BLOCK_TAGS = {
    "p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
    "section", "article", "header", "footer", "ul", "ol", "table",
}


class UrlFetchError(Exception):
    """URL güvenli biçimde çekilemediğinde fırlatılır."""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in SKIP_TAGS:
            self._skip_depth += 1
        elif tag in BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self._parts.append(data.strip())

    def get_text(self) -> str:
        text = " ".join(self._parts)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\s*\n\s*", "\n", text)
        return re.sub(r"\n{3,}", "\n\n", text).strip()


def _validate_url(url: str) -> str:
    """URL'yi SSRF'e karşı doğrular ve host'unu döner."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UrlFetchError("Yalnızca http ve https adresleri desteklenir.")
    host = parsed.hostname
    if not host:
        raise UrlFetchError("Geçersiz URL: sunucu adı bulunamadı.")

    allowed = [d.strip().lower() for d in settings.ALLOWED_JOB_DOMAINS.split(",") if d.strip()]
    if allowed:
        host_lower = host.lower()
        if not any(host_lower == d or host_lower.endswith(f".{d}") for d in allowed):
            raise UrlFetchError(
                f"Bu alan adından içerik çekilmesine izin verilmiyor: {host}. "
                "İlan metnini doğrudan yapıştırabilirsiniz."
            )

    # DNS çözümlemesi: tüm sonuçlar public olmalı (SSRF koruması)
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror:
        raise UrlFetchError(f"Sunucu adı çözümlenemedi: {host}")

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise UrlFetchError(
                "Güvenlik nedeniyle yerel/özel ağ adreslerinden içerik çekilemez."
            )
    return host


def _fetch_job_text_standard(url: str) -> str:
    """İlan sayfasının metnini güvenli biçimde çeker.

    Yönlendirmeler elle takip edilir; her adım yeniden doğrulanır ki
    public bir adres özel bir ağa yönlendiremesin.
    """
    max_bytes = settings.MAX_FETCH_KB * 1024
    current = url

    with httpx.Client(
        timeout=settings.FETCH_TIMEOUT_SECONDS,
        follow_redirects=False,
        headers={"User-Agent": "CV-Agent/1.0 (+job-posting-import)"},
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            _validate_url(current)
            try:
                response = client.get(current)
            except httpx.HTTPError as exc:
                raise UrlFetchError(f"Sayfa alınamadı: {exc}")

            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise UrlFetchError("Yönlendirme hedefi bulunamadı.")
                current = str(response.url.join(location))
                continue

            if response.status_code >= 400:
                raise UrlFetchError(
                    f"Sayfa alınamadı (HTTP {response.status_code})."
                )

            content_type = response.headers.get("content-type", "")
            if not any(t in content_type for t in ("text/html", "text/plain", "application/xhtml")):
                raise UrlFetchError(
                    f"Desteklenmeyen içerik türü: {content_type or 'bilinmiyor'}"
                )

            body = response.content[:max_bytes]
            html = body.decode(response.encoding or "utf-8", errors="replace")
            parser = _TextExtractor()
            parser.feed(html)
            text = parser.get_text()
            if len(text) < 100:
                raise UrlFetchError(
                    "Sayfadan anlamlı bir ilan metni çıkarılamadı."
                )
            return text

    raise UrlFetchError("Çok fazla yönlendirme.")

def fetch_job_text(url: str) -> str:
    """İlan sayfasının metnini güvenli biçimde çeker.

    Önce standart bir istek atılır, başarısız olursa veya yetersiz metin çıkarsa
    jina reader API kullanılarak güvenilir bir metin elde edilir.
    """
    try:
        return _fetch_job_text_standard(url)
    except UrlFetchError:
        # Fallback to Jina Reader
        with httpx.Client(timeout=settings.FETCH_TIMEOUT_SECONDS) as client:
            try:
                jina_url = f"https://r.jina.ai/{url}"
                response = client.get(jina_url, headers={"Accept": "text/plain"})
                response.raise_for_status()
                text = response.text.strip()
                if len(text) < 100:
                    raise UrlFetchError("Jina Reader ile de anlamlı metin çekilemedi.")
                return text
            except Exception as exc:
                raise UrlFetchError(
                    f"Sayfa alınamadı. Standart çekim ve Jina Reader denemeleri başarısız: {exc}. "
                    "İlan metnini doğrudan yapıştırmayı deneyin."
                )
