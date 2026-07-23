from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime

from services.pdf_validation import validate_reference_pdfs, PdfValidationError


class ProjectCreate(BaseModel):
    nom: str = Field(..., min_length=1)
    pays: str = Field(..., min_length=1)
    secteur: str = Field(..., min_length=1)
    bailleur: str = Field(..., min_length=1)
    probleme_principal: str = Field(..., min_length=1)
    objectif_global: str = Field(..., min_length=1)
    objectifs_specifiques: List[str] = Field(default_factory=list)
    population_cible: Optional[str] = None
    nombre_beneficiaires: Optional[int] = None
    duree_mois: Optional[int] = None
    date_debut: Optional[str] = None
    contraintes: Optional[str] = None
    risques_identifies: Optional[str] = None
    budget_total: Optional[float] = None
    source_financement: Optional[str] = None
    part_couts_operationnels: Optional[int] = 30
    generer_note_conceptuelle: bool = False
    inclure_resume_executif: bool = False
    inclure_perennisation: bool = False
    # PDFs de référence encodés en base64 (optionnel)
    reference_pdfs: Optional[List[str]] = None

    @field_validator("reference_pdfs")
    @classmethod
    def _check_pdfs(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if not v:
            return v
        try:
            validate_reference_pdfs(v)
        except PdfValidationError as e:
            raise ValueError(str(e))
        return v


class ProjectResponse(BaseModel):
    id: int
    nom: str
    pays: str
    secteur: str
    bailleur: str
    probleme_principal: str
    objectif_global: str
    budget_total: Optional[float]
    duree_mois: Optional[int]
    created_at: datetime
    docx_path: Optional[str] = None

    class Config:
        from_attributes = True
