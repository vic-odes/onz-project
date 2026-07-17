"""Limiteur de débit partagé (slowapi).

Défini dans un module autonome pour être importé à la fois par `main` (câblage
de l'app + handler d'exception) et par les routers (décorateur `@limiter.limit`)
sans créer d'import circulaire.

Le stockage par défaut est en mémoire — suffisant pour un déploiement mono-worker.
Pour plusieurs workers/instances, configurer un backend Redis via `RATELIMIT_STORAGE_URI`.
"""
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# Désactivable en test/dev via AUTH_RATE_LIMIT_ENABLED=false
_enabled = os.getenv("AUTH_RATE_LIMIT_ENABLED", "true").lower() != "false"

limiter = Limiter(
    key_func=get_remote_address,
    enabled=_enabled,
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
)

# Limites configurables par variable d'environnement (par IP).
LOGIN_RATE_LIMIT = os.getenv("LOGIN_RATE_LIMIT", "5/minute")
REGISTER_RATE_LIMIT = os.getenv("REGISTER_RATE_LIMIT", "3/minute")
