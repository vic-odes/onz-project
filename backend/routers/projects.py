import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from dependencies import get_current_user
from models.project import Project
from models.user import User
from schemas.project import ProjectResponse
import json

logger = logging.getLogger(__name__)
router = APIRouter()


def _owned_or_404(db: Session, project_id: int, user_id: int) -> Project:
    """Retourne le projet si et seulement s'il appartient à l'utilisateur courant."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user_id)
        .first()
    )
    if not project:
        # 404 plutôt que 403 pour ne pas révéler l'existence d'un projet d'un autre user
        raise HTTPException(status_code=404, detail="Projet non trouvé")
    return project


@router.get("/", response_model=List[ProjectResponse])
def list_projects(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Project)
        .filter(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{project_id}")
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _owned_or_404(db, project_id, current_user.id)
    return {
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


@router.get("/{project_id}/download")
def download_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _owned_or_404(db, project_id, current_user.id)
    if not project.docx_path or not Path(project.docx_path).exists():
        raise HTTPException(status_code=404, detail="Document non disponible")
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in project.nom)
    filename = f"{safe_name.replace(' ', '_')}_ONZ.docx"
    return FileResponse(
        path=project.docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _owned_or_404(db, project_id, current_user.id)
    if project.docx_path:
        try:
            Path(project.docx_path).unlink(missing_ok=True)
            logger.debug("Fichier DOCX supprimé : %s", project.docx_path)
        except Exception:
            logger.exception("Erreur suppression fichier DOCX")
    db.delete(project)
    db.commit()
    return {"message": "Projet supprimé avec succès"}
