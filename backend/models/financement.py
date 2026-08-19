from sqlalchemy import Boolean, Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class RechercheFinancement(Base):
    """Une recherche de financement lancée pour un projet déjà monté.

    `criteres`/`resultats` sont stockés en JSON texte (même pattern que
    `Project.generated_content`) — pas de table normalisée par opportunité,
    cohérent avec la philosophie « app légère » du projet.
    """

    __tablename__ = "recherches_financement"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    criteres = Column(Text, nullable=False)  # JSON — profil du projet envoyé au LLM
    resultats = Column(Text, nullable=False)  # JSON — ResultatsFinancement validé
    recherche_live = Column(Boolean, nullable=False, default=False)  # web_search activé pour ce modèle
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User")
    project = relationship("Project")
