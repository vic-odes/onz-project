import os
import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routers import generate, projects, documents
from database import init_db
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
# Réduire le bruit des bibliothèques tierces
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
# logging.getLogger("litellm").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logger = logging.getLogger("main")

app = FastAPI(
    title="ONZ Projet API",
    description="API de génération de documents de projets de développement international",
    version="1.0.0",
)

_cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate.router, prefix="/api/generate", tags=["Génération"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projets"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])


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
    logger.info("API démarrée — modèle=%s", os.getenv("LLM_MODEL", "claude-sonnet-4-20250514"))


@app.get("/")
def root():
    return {"message": "ONZ Projet API — opérationnelle", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}
