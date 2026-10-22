"""Redis tabanlı, sabit pencereli (fixed-window) basit hız sınırlayıcı.

Kimlik doğrulama uçlarını (login, register, şifre sıfırlama) brute-force
denemelerine ve gereksiz maliyete karşı korumak için kullanılır. IP bazlıdır
(kullanıcı henüz kimliği doğrulanmamış olabileceğinden e-posta/kullanıcı
bazlı sınırlama bu uçlarda uygulanamaz).

Redis'e erişilemezse İSTEK REDDEDİLMEZ (fail-open): bir altyapı sorunu
yüzünden tüm kullanıcıların giriş yapamaz hale gelmesi, brute-force riskinden
daha kötü bir kullanıcı deneyimi sonucu doğurur.
"""

import logging

import redis
from fastapi import HTTPException, Request, status

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def rate_limiter(key_prefix: str, max_requests: int, window_seconds: int):
    """Belirli bir uç için hız sınırlayıcı FastAPI bağımlılığı üretir."""

    def dependency(request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return

        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{key_prefix}:{client_ip}"

        try:
            client = _get_redis()
            count = client.incr(key)
            if count == 1:
                client.expire(key, window_seconds)
            ttl = client.ttl(key)
        except redis.RedisError:
            logger.warning("Rate limiter Redis'e erişemedi; istek engellenmeden geçiriliyor.")
            return

        if count > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Çok fazla deneme yapıldı. Lütfen bir süre sonra tekrar deneyin.",
                headers={"Retry-After": str(max(ttl, 1))},
            )

    return dependency
