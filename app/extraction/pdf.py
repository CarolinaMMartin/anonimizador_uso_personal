"""Extracción de texto desde PDF digital (pdfplumber, sin OCR)."""
import io
import logging

import pdfplumber

from app.extraction.pdf_cleanup import clean_pdf_text, merge_lines_to_paragraphs

logger = logging.getLogger(__name__)

MIN_DIGITAL_CHARS = 15


def recognize_page_without_text(page, page_number: int) -> str:
    """Punto de enganche para reconocer páginas escaneadas (OCR).

    Recibe cada página que no tiene texto seleccionable y devuelve el texto
    reconocido. Hoy no reconoce nada y devuelve una cadena vacía, por lo que
    esas páginas se omiten. Para sumar OCR alcanza con implementar esta
    función: ``extract_pdf`` ya limpia e intercala en orden lo que devuelva.

    ``page`` es la página de pdfplumber y ``page_number`` empieza en 1.
    """
    return ""


def extract_pdf(data: bytes) -> str:
    """Extrae solo la capa de texto nativa del PDF.

    PDFs mixtos (portada escaneada + páginas digitales) están soportados:
    las páginas sin texto seleccionable pasan por
    ``recognize_page_without_text`` y, si no devuelve texto, se omiten.
    """
    parts: list[str] = []
    empty_pages = 0
    total_pages = 0

    with pdfplumber.open(io.BytesIO(data)) as doc:
        total_pages = len(doc.pages)
        for page_number, page in enumerate(doc.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            if not page_text:
                page_text = (recognize_page_without_text(page, page_number) or "").strip()
            if not page_text:
                empty_pages += 1
                continue
            cleaned = clean_pdf_text(page_text)
            parts.append(merge_lines_to_paragraphs(cleaned))

    text = "\n\n".join(p for p in parts if p).strip()

    if not text:
        raise ValueError(
            "Este PDF no tiene texto digital (parece escaneado o es solo imagen). "
            "El reconocimiento de documentos escaneados todavía no está disponible. "
            "Usá un PDF exportado con texto seleccionable o convertilo a Word (.docx)."
        )

    if len(text) < MIN_DIGITAL_CHARS:
        raise ValueError(
            "El PDF tiene muy poco texto digital. Verificá que no sea un escaneo "
            "o un archivo dañado."
        )

    if empty_pages:
        logger.info(
            "PDF mixto: %d de %d páginas sin texto digital (omitidas)",
            empty_pages,
            total_pages,
        )

    return text
