import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import generate, projects
from database import init_db
from dotenv import load_dotenv

load_dotenv()

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


@app.on_event("startup")
async def startup_event():
    init_db()


@app.get("/")
def root():
    return {"message": "ONZ Projet API — opérationnelle", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}
