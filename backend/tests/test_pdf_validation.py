"""Tests des limites et validations sur les PDFs uploadés."""
import base64

import pytest

from services.pdf_validation import (
    MAX_PDF_BYTES,
    MAX_REFERENCE_PDFS_COUNT,
    MAX_TOTAL_PDFS_BYTES,
    PdfValidationError,
    validate_pdf_b64,
    validate_reference_pdfs,
)


def _b64(payload: bytes) -> str:
    return base64.b64encode(payload).decode("ascii")


def _valid_pdf(size: int = 256) -> str:
    """Construit un blob PDF minimal (signature + padding)."""
    body = b"%PDF-1.4\n" + b"x" * max(0, size - 9)
    return _b64(body)


def test_accepts_minimal_pdf():
    decoded = validate_pdf_b64(_valid_pdf())
    assert decoded.startswith(b"%PDF-")


def test_rejects_empty_string():
    with pytest.raises(PdfValidationError, match="vide"):
        validate_pdf_b64("")


def test_rejects_whitespace_only():
    with pytest.raises(PdfValidationError, match="vide"):
        validate_pdf_b64("   \n  ")


def test_rejects_non_pdf_magic_bytes():
    fake = _b64(b"PK\x03\x04zip-not-pdf")
    with pytest.raises(PdfValidationError, match="pas un fichier PDF"):
        validate_pdf_b64(fake)


def test_rejects_invalid_base64():
    with pytest.raises(PdfValidationError, match="base64"):
        validate_pdf_b64("!!!not-base64!!!")


def test_rejects_oversized_pdf():
    # Construire un PDF dont la taille décodée dépasse la limite
    oversized = _b64(b"%PDF-" + b"x" * (MAX_PDF_BYTES + 1024))
    with pytest.raises(PdfValidationError, match="volumineux"):
        validate_pdf_b64(oversized)


def test_aggregate_rejects_too_many_files():
    pdfs = [_valid_pdf() for _ in range(MAX_REFERENCE_PDFS_COUNT + 1)]
    with pytest.raises(PdfValidationError, match="Trop de fichiers"):
        validate_reference_pdfs(pdfs)


def test_aggregate_accepts_exactly_max_count():
    pdfs = [_valid_pdf() for _ in range(MAX_REFERENCE_PDFS_COUNT)]
    validate_reference_pdfs(pdfs)  # ne doit pas lever


def test_aggregate_rejects_total_size():
    # Chaque PDF fait ~7 MB, 5 fichiers > 30 MB cumulés
    big_chunk = b"%PDF-" + b"a" * (7 * 1024 * 1024)
    pdfs = [_b64(big_chunk) for _ in range(MAX_REFERENCE_PDFS_COUNT)]
    with pytest.raises(PdfValidationError, match="cumul"):
        validate_reference_pdfs(pdfs)


def test_aggregate_propagates_individual_errors():
    pdfs = [_valid_pdf(), _b64(b"not-a-pdf-at-all")]
    with pytest.raises(PdfValidationError, match="PDF #2"):
        validate_reference_pdfs(pdfs)


def test_constants_reasonable():
    # Garde-fou : si quelqu'un assouplit les limites par mégarde
    assert MAX_PDF_BYTES == 10 * 1024 * 1024
    assert MAX_TOTAL_PDFS_BYTES == 30 * 1024 * 1024
    assert MAX_REFERENCE_PDFS_COUNT == 5
