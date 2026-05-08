import asyncio
import io
import json
import logging
import time
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from database import save_project
from dependencies import get_current_user
from models.user import User
from schemas.project import ProjectCreate
from services import ai_service, docx_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/")
async def generate_document(
    project: ProjectCreate,
    current_user: User = Depends(get_current_user),
):
    """Endpoint bloquant historique — conservé pour les clients qui ne consomment pas SSE."""
    project_dict = project.model_dump()
    reference_pdfs = project_dict.pop("reference_pdfs", None) or []

    logger.info(
        "Génération démarrée — user=%d projet=%r pays=%r secteur=%r bailleur=%r pdfs=%d",
        current_user.id, project.nom, project_dict.get("pays"), project_dict.get("secteur"),
        project_dict.get("bailleur"), len(reference_pdfs),
    )

    try:
        generated = await ai_service.generate_project_content(project_dict, reference_pdfs or None)
        logger.info("Génération IA réussie — clés reçues: %s", list(generated.keys()))
    except json.JSONDecodeError as e:
        logger.exception("JSON invalide retourné par le modèle")
        raise HTTPException(status_code=502, detail=f"Le modèle IA a retourné un JSON invalide : {str(e)}")
    except ValidationError as e:
        missing = [".".join(str(p) for p in err["loc"]) for err in e.errors()]
        logger.error("Sortie LLM invalide — champs problématiques : %s", missing)
        raise HTTPException(
            status_code=502,
            detail=(
                "Le modèle IA a retourné une réponse incomplète "
                f"(champ(s) problématique(s) : {', '.join(missing)}). Réessayez."
            ),
        )
    except Exception as e:
        logger.exception("Erreur lors de la génération IA")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération IA : {str(e)}")

    try:
        docx_bytes = docx_service.create_word_document(project_dict, generated)
        logger.info("Document Word créé — taille=%d octets", len(docx_bytes))
    except Exception as e:
        logger.exception("Erreur lors de la création du document Word")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du document Word : {str(e)}")

    try:
        save_project(project_dict, generated, current_user.id, docx_bytes)
        logger.debug("Projet et document DOCX sauvegardés")
    except Exception:
        logger.exception("Erreur sauvegarde SQLite (non bloquant)")

    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in project.nom)
    filename = f"{safe_name.replace(' ', '_')}_ONZ.docx"
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ──────────────────────────────────────────────────────────────────────────
# Streaming SSE
# ──────────────────────────────────────────────────────────────────────────

# Coalesce les ticks de progression : un tick toutes les ~250ms suffit côté UI
# et évite de saturer le réseau avec des centaines de petits events par seconde.
_PROGRESS_TICK_SECONDS = 0.25


def _sse(event: str, data: dict) -> bytes:
    """Encode un événement SSE conforme à text/event-stream."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


async def _generate_events(
    project: ProjectCreate, user_id: int
) -> AsyncIterator[bytes]:
    """Pipeline SSE : génération IA streamée → validation → docx → persistance.

    Tous les chemins d'erreur émettent un event `error` puis terminent proprement
    le stream. Le client n'a donc jamais à inspecter le statut HTTP final.
    """
    project_dict = project.model_dump()
    reference_pdfs = project_dict.pop("reference_pdfs", None) or []
    project_name = project.nom

    logger.info(
        "Streaming démarré — user=%d projet=%r pdfs=%d",
        user_id, project_name, len(reference_pdfs),
    )

    yield _sse("phase", {"name": "generation", "label": "Génération du contenu par l'IA"})

    total_chars = 0
    last_emit = 0.0
    try:
        # Heartbeat initial : utile pour que la barre quitte 0 % avant le premier token.
        yield _sse("progress", {"phase": "generation", "chars": 0})

        async for event, payload in ai_service.stream_project_content(
            project_dict, reference_pdfs or None
        ):
            if event == "token":
                total_chars += payload["chars"]
                now = time.monotonic()
                if now - last_emit >= _PROGRESS_TICK_SECONDS:
                    last_emit = now
                    yield _sse("progress", {"phase": "generation", "chars": total_chars})
            elif event == "validated":
                generated = payload["content"]
                yield _sse("progress", {"phase": "generation", "chars": total_chars})
                logger.info("Génération streamée réussie — %d caractères", total_chars)
                break
        else:
            # Le générateur s'est épuisé sans `validated` — invariant violé
            yield _sse("error", {"message": "Le modèle n'a pas retourné de contenu valide."})
            return

    except json.JSONDecodeError as e:
        logger.exception("JSON invalide retourné par le modèle (stream)")
        yield _sse("error", {"message": f"Le modèle IA a retourné un JSON invalide : {e}"})
        return
    except ValidationError as e:
        missing = [".".join(str(p) for p in err["loc"]) for err in e.errors()]
        logger.error("Sortie LLM invalide (stream) — champs : %s", missing)
        yield _sse("error", {
            "message": (
                "Le modèle IA a retourné une réponse incomplète "
                f"(champ(s) : {', '.join(missing)}). Réessayez."
            ),
        })
        return
    except ValueError as e:
        # Tronqué (max_tokens) ou réponse vide — message déjà localisé en français.
        logger.warning("Stream LLM rejeté : %s", e)
        yield _sse("error", {"message": str(e)})
        return
    except Exception as e:
        logger.exception("Erreur inattendue pendant le streaming LLM")
        yield _sse("error", {"message": f"Erreur lors de la génération IA : {e}"})
        return

    # Phase 2 : DOCX (CPU-bound, on le pousse dans un thread pour ne pas bloquer la boucle)
    yield _sse("phase", {"name": "docx", "label": "Mise en forme du document Word"})
    try:
        docx_bytes = await asyncio.to_thread(
            docx_service.create_word_document, project_dict, generated
        )
        logger.info("Document Word créé — taille=%d octets", len(docx_bytes))
    except Exception as e:
        logger.exception("Erreur création DOCX (stream)")
        yield _sse("error", {"message": f"Erreur lors de la création du document Word : {e}"})
        return

    # Phase 3 : persistance — non bloquante sur erreur, on continue à servir le doc
    yield _sse("phase", {"name": "persistance", "label": "Enregistrement du projet"})
    project_id = None
    try:
        saved = await asyncio.to_thread(
            save_project, project_dict, generated, user_id, docx_bytes
        )
        # save_project ferme sa session après refresh — l'id est déjà chargé en mémoire.
        project_id = getattr(saved, "id", None)
        logger.debug("Projet streamé sauvegardé — id=%s", project_id)
    except Exception:
        logger.exception("Erreur sauvegarde SQLite (stream, non bloquant)")

    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in project_name)
    filename = f"{safe_name.replace(' ', '_')}_ONZ.docx"

    yield _sse("done", {
        "project_id": project_id,
        "filename": filename,
        "chars": total_chars,
    })


@router.post("/stream")
async def generate_document_stream(
    project: ProjectCreate,
    current_user: User = Depends(get_current_user),
):
    """Streaming SSE du pipeline de génération.

    Le client lit les événements suivants :
      - `phase`    : changement de phase ({name, label})
      - `progress` : avancement de la phase courante ({phase, chars})
      - `error`    : erreur fatale, le stream se termine ({message})
      - `done`     : succès ({project_id, filename, chars})

    Une fois `done` reçu, le client appelle `/api/projects/{project_id}/download`
    pour récupérer le `.docx`.
    """
    return StreamingResponse(
        _generate_events(project, current_user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # désactive le buffering nginx si présent
            "Connection": "keep-alive",
        },
    )
