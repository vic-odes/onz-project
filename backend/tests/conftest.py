"""Configuration pytest commune.

Ajoute le dossier `backend/` au sys.path pour que `from services...`
fonctionne quand pytest est lancé depuis la racine ou depuis backend/.
"""
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Secret JWT déterministe pour tous les tests qui en ont besoin (auth_service).
os.environ.setdefault("JWT_SECRET_KEY", "test-" + "x" * 64)
