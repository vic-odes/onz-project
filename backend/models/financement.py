from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class RechercheFinancement(Base):
    """Une recherche de financement lancée pour un projet déjà monté.

    `criteres`/`resultats` sont stockés en JSON texte (même pattern que
    `Project.generated_content`) — pas de table normalisée par opportunité,
    cohérent avec la philosophie « app légère » du projet.

    L'appel LLM (recherche web incluse) peut prendre plusieurs minutes — trop
    long pour une requête HTTP bloquante derrière un ingress qui a son propre
    timeout (ex. 240s par défaut sur Azure Container Apps). La recherche
    s'exécute donc en tâche de fond : la ligne est créée en `status="en_cours"`
    avec `resultats="{}"`, puis mise à jour à la fin (`termine`/`erreur`). Le
    frontend récupère le résultat par sondage (`GET /api/financements/{id}`).
    """

    __tablename__ = "recherches_financement"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    criteres = Column(Text, nullable=False)  # JSON — profil du projet envoyé au LLM
    resultats = Column(Text, nullable=False)  # JSON — ResultatsFinancement validé (ou "{}" tant qu'en cours)
    recherche_live = Column(Boolean, nullable=False, default=False)  # web_search activé pour ce modèle
    status = Column(String, nullable=False, default="en_cours")  # en_cours | termine | erreur
    erreur = Column(Text, nullable=True)  # message d'erreur si status="erreur"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User")
    project = relationship("Project")
