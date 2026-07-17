import os
import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./onz_projects.db")
DOCUMENTS_DIR = Path(__file__).parent / "documents"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_project(project_data: dict, generated_content: dict, user_id: int, docx_bytes: bytes | None = None):
    from models.project import Project
    DOCUMENTS_DIR.mkdir(exist_ok=True)
    db = SessionLocal()
    try:
        project = Project(
            user_id=user_id,
            nom=project_data.get("nom", ""),
            pays=project_data.get("pays", ""),
            secteur=project_data.get("secteur", ""),
            bailleur=project_data.get("bailleur", ""),
            probleme_principal=project_data.get("probleme_principal", ""),
            objectif_global=project_data.get("objectif_global", ""),
            budget_total=project_data.get("budget_total"),
            duree_mois=project_data.get("duree_mois"),
            generated_content=json.dumps(generated_content, ensure_ascii=False),
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        if docx_bytes:
            safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in project.nom)
            filename = f"{project.id}_{safe_name.replace(' ', '_')}_ONZ.docx"
            path = DOCUMENTS_DIR / filename
            path.write_bytes(docx_bytes)
            project.docx_path = str(path)
            db.commit()

        return project
    finally:
        db.close()


def init_db():
    """Applique les migrations Alembic jusqu'à `head`.

    Remplace l'ancien `Base.metadata.create_all` + ALTER TABLE ad-hoc.
    Toute évolution de schéma passe désormais par `alembic revision --autogenerate`.
    """
    from alembic import command
    from alembic.config import Config

    # Importer tous les modèles pour qu'ils soient disponibles si Alembic relit Base
    import models  # noqa: F401

    backend_dir = Path(__file__).resolve().parent
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

    logger.info("Application des migrations Alembic — DB=%s", DATABASE_URL)
    command.upgrade(alembic_cfg, "head")
