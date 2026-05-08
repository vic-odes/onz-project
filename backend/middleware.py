"""Middleware ASGI : limite de taille de body.

Première ligne de défense — rejet immédiat sur Content-Length avant que le corps
ne soit lu en mémoire. La validation Pydantic des PDFs (taille décodée + magic
bytes) reste la 2ᵉ ligne, et couvre les requêtes en chunked transfer (sans header
Content-Length).
"""

import logging

logger = logging.getLogger(__name__)

# 50 MB — laisse la place pour 30 MB de PDFs base64 (×4/3 ≈ 40 MB) + JSON overhead.
DEFAULT_MAX_BODY_SIZE = 50 * 1024 * 1024


class BodySizeLimitMiddleware:
    def __init__(self, app, max_body_size: int = DEFAULT_MAX_BODY_SIZE):
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    length = int(value.decode("latin-1"))
                except ValueError:
                    continue
                if length > self.max_body_size:
                    logger.warning(
                        "Requête rejetée — Content-Length %d > limite %d (%s %s)",
                        length,
                        self.max_body_size,
                        scope.get("method"),
                        scope.get("path"),
                    )
                    await send(
                        {
                            "type": "http.response.start",
                            "status": 413,
                            "headers": [
                                (b"content-type", b"application/json; charset=utf-8"),
                            ],
                        }
                    )
                    await send(
                        {
                            "type": "http.response.body",
                            "body": (
                                b'{"detail":"Corps de requ\xc3\xaate trop volumineux '
                                + f"(max {self.max_body_size // (1024 * 1024)} MB).".encode("utf-8")
                                + b'"}'
                            ),
                        }
                    )
                    return
                break

        await self.app(scope, receive, send)
