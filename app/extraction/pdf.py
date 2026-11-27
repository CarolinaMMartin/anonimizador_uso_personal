"""Extracción de texto desde PDF digital (pdfplumber, sin OCR)."""
import io
from dataclasses import dataclass

import pdfplumber

from app.extraction.pdf_cleanup import clean_pdf_text, merge_lines_to_paragraphs

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


@dataclass
class PdfExtraction:
    text: str
    page_count: int
    omitted_pages: list[int]


def extract_pdf(data: bytes) -> str:
    return extract_pdf_with_pages(data).text


def extract_pdf_with_pages(data: bytes) -> PdfExtraction:
    """Extrae el texto utilizable e identifica páginas omitidas (numeradas desde 1)."""
    parts: list[str] = []
    omitted: list[int] = []

    with pdfplumber.open(io.BytesIO(data)) as doc:
        total_pages = len(doc.pages)
        for number, page in enumerate(doc.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            if not page_text:
                page_text = (recognize_page_without_text(page, number) or "").strip()
            cleaned = merge_lines_to_paragraphs(clean_pdf_text(page_text))
            if cleaned:
                parts.append(cleaned)
            else:
                omitted.append(number)

    text = "\n\n".join(parts).strip()

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

    return PdfExtraction(text, total_pages, omitted)
