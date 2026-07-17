"""Validation des PDFs reçus en base64.

Trois lignes de défense :
1. Limite stricte sur la taille de la chaîne base64 (rejet sans décoder).
2. Décodage et vérification de la magic-bytes signature `%PDF-`.
3. Limites agrégées (nombre de fichiers, taille totale) appliquées par les schémas.
"""

import base64
import binascii

# Limites — modifiables via constantes uniquement (pas d'env var pour l'instant
# pour éviter qu'elles soient relâchées sans review).
MAX_PDF_BYTES = 10 * 1024 * 1024            # 10 MB par PDF (après décodage)
MAX_TOTAL_PDFS_BYTES = 30 * 1024 * 1024     # 30 MB pour la somme des PDFs d'une requête
MAX_REFERENCE_PDFS_COUNT = 5                # max 5 PDFs de référence
PDF_MAGIC = b"%PDF-"

# Coefficient base64 : 4 caractères encodent 3 octets, donc taille_b64 ≈ taille_brute * 4/3.
# On garde une marge de 5 % pour les sauts de ligne / padding inattendus.
_MAX_B64_LEN = int(MAX_PDF_BYTES * 4 / 3 * 1.05)


class PdfValidationError(ValueError):
    """Erreur de validation d'un PDF (taille, format, magic bytes)."""


def validate_pdf_b64(b64: str, *, label: str = "PDF") -> bytes:
    """Valide et décode un PDF encodé en base64.

    Lève :
      - PdfValidationError si la chaîne est vide, trop longue, mal encodée, ou ne
        commence pas par la signature %PDF-.

    Retourne :
      - Les octets décodés du PDF (utiles si l'appelant veut les stocker).
    """
    if not b64 or not b64.strip():
        raise PdfValidationError(f"{label} : contenu vide.")

    if len(b64) > _MAX_B64_LEN:
        raise PdfValidationError(
            f"{label} : trop volumineux (limite {MAX_PDF_BYTES // (1024 * 1024)} MB par fichier)."
        )

    try:
        # validate=True rejette les caractères non-base64 — empêche du contenu arbitraire
        decoded = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError) as e:
        raise PdfValidationError(f"{label} : encodage base64 invalide ({e}).")

    if len(decoded) > MAX_PDF_BYTES:
        raise PdfValidationError(
            f"{label} : trop volumineux après décodage "
            f"(limite {MAX_PDF_BYTES // (1024 * 1024)} MB)."
        )

    if not decoded.startswith(PDF_MAGIC):
        raise PdfValidationError(f"{label} : ce n'est pas un fichier PDF valide.")

    return decoded


def validate_reference_pdfs(pdfs_b64: list[str]) -> None:
    """Applique toutes les limites agrégées à une liste de PDFs.

    Chaque entrée est validée individuellement par `validate_pdf_b64`.
    Lève `PdfValidationError` si une limite (nombre, taille totale) est dépassée.
    """
    if len(pdfs_b64) > MAX_REFERENCE_PDFS_COUNT:
        raise PdfValidationError(
            f"Trop de fichiers PDF (max {MAX_REFERENCE_PDFS_COUNT})."
        )
    total = 0
    for i, b64 in enumerate(pdfs_b64, 1):
        decoded = validate_pdf_b64(b64, label=f"PDF #{i}")
        total += len(decoded)
        if total > MAX_TOTAL_PDFS_BYTES:
            raise PdfValidationError(
                f"Taille cumulée des PDFs trop élevée "
                f"(limite {MAX_TOTAL_PDFS_BYTES // (1024 * 1024)} MB)."
            )
