from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.sql import func
from database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    pays = Column(String, nullable=False)
    secteur = Column(String, nullable=False)
    bailleur = Column(String, nullable=False)
    probleme_principal = Column(Text)
    objectif_global = Column(Text)
    budget_total = Column(Float, nullable=True)
    duree_mois = Column(Integer, nullable=True)
    generated_content = Column(Text)  # JSON stocké en texte
    created_at = Column(DateTime(timezone=True), server_default=func.now())
