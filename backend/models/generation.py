from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class GenerationJob(Base):
    """Un job de génération de document démarré depuis le formulaire projet.

    L'appel LLM (jusqu'à plusieurs dizaines de milliers de tokens, PDFs joints
    en natif) peut prendre plus d'une minute — assez pour que le navigateur
    coupe la requête (ex. `net::ERR_NETWORK_IO_SUSPENDED` si l'appareil se met
    en veille pendant l'attente, ou l'onglet reste longtemps en arrière-plan).
    Même pattern que `RechercheFinancement` : la ligne est créée en
    `status="en_cours"`, la génération tourne en tâche de fond, puis la ligne
    est mise à jour à la fin (`termine` avec `project_id` renseigné, ou
    `erreur`). Le frontend récupère le résultat par sondage
    (`GET /api/generate/etat/{id}`).
    """

    __tablename__ = "generation_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String, nullable=False, default="en_cours")  # en_cours | termine | erreur
    erreur = Column(Text, nullable=True)  # message d'erreur si status="erreur"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User")
    project = relationship("Project")
