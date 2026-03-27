from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.project import Project
from schemas.project import ProjectResponse
import json

router = APIRouter()


@router.get("/", response_model=List[ProjectResponse])
def list_projects(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
    return projects


@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    result = {
        "id": project.id,
        "nom": project.nom,
        "pays": project.pays,
        "secteur": project.secteur,
        "bailleur": project.bailleur,
        "probleme_principal": project.probleme_principal,
        "objectif_global": project.objectif_global,
        "budget_total": project.budget_total,
        "duree_mois": project.duree_mois,
        "created_at": project.created_at,
        "generated_content": json.loads(project.generated_content) if project.generated_content else {},
    }
    return result


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    db.delete(project)
    db.commit()
    return {"message": "Projet supprimé avec succès"}
