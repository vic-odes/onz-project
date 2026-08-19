import os
import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from routers import generate, projects, documents, auth, financements
from database import init_db
from middleware import BodySizeLimitMiddleware
from rate_limit import limiter
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
# Réduire le bruit des bibliothèques tierces
for _lib in ("httpx", "httpcore", "litellm", "LiteLLM",
             "openai", "openai._base_client", "uvicorn.access"):
    logging.getLogger(_lib).setLevel(logging.WARNING)

logger = logging.getLogger("main")

app = FastAPI(
    title="ONZ Projet API",
    description="API de génération de documents de projets de développement international",
    version="1.0.0",
)

# Limitation de débit (brute-force /login, spam /register) — voir rate_limit.py
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition", "X-Project-Id"],  # docx + id du projet créé
    max_age=600,
)
app.add_middleware(BodySizeLimitMiddleware)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentification"])
app.include_router(generate.router, prefix="/api/generate", tags=["Génération"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projets"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(financements.router, prefix="/api/financements", tags=["Financements"])


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    logger.info("→ %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled exception for %s %s", request.method, request.url.path)
        raise
    elapsed = (time.perf_counter() - start) * 1000
    logger.info("← %s %s %d (%.0fms)", request.method, request.url.path, response.status_code, elapsed)
    return response


@app.on_event("startup")
async def startup_event():
    init_db()
    if not os.getenv("JWT_SECRET_KEY"):
        logger.error(
            "JWT_SECRET_KEY n'est pas défini — l'authentification échouera. "
            "Génère un secret avec : python -c \"import secrets; print(secrets.token_urlsafe(64))\""
        )
    logger.info("API démarrée — modèle=%s", os.getenv("LLM_MODEL", "claude-sonnet-4-20250514"))


@app.get("/")
def root():
    return {"message": "ONZ Projet API — opérationnelle", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}
