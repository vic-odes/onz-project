"""Utilitaires HTTP transverses (sans dépendance FastAPI)."""

from urllib.parse import quote


def content_disposition_attachment(filename: str) -> str:
    """En-tête `Content-Disposition: attachment` robuste (RFC 6266).

    Les en-têtes HTTP sont limités à l'ASCII/latin-1. Un nom de fichier accentué
    (« Café », « Éducation ») ou non-latin casse la réponse si on l'injecte brut.
    On fournit donc deux formes, comme Starlette pour `FileResponse` :
    - `filename=`  : repli ASCII pur (tout caractère non-ASCII → `_`) ;
    - `filename*=` : version UTF-8 encodée en pourcentage (RFC 5987), lue en
      priorité par les navigateurs modernes, qui préserve les accents.
    """
    name = (filename or "").strip() or "fichier"
    ascii_fallback = "".join(
        c if (c.isascii() and (c.isalnum() or c in " _-.")) else "_" for c in name
    ).replace(" ", "_")
    utf8_encoded = quote(name, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{utf8_encoded}"
