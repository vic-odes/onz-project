import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./onz_projects.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_project(project_data: dict, generated_content: dict):
    from models.project import Project
    db = SessionLocal()
    try:
        project = Project(
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
        return project
    finally:
        db.close()


def init_db():
    from models.project import Project  # noqa: F401
    Base.metadata.create_all(bind=engine)
