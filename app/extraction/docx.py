"""Extracción de texto desde DOCX."""
import io

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def _block_text(container):
    for block in container.iter_inner_content():
        if isinstance(block, Paragraph):
            if block.text.strip():
                yield block.text.strip()
        elif isinstance(block, Table):
            seen_cells = set()
            for row in block.rows:
                cells = []
                for cell in row.cells:
                    if cell._tc in seen_cells:
                        continue
                    seen_cells.add(cell._tc)
                    value = '\n'.join(_block_text(cell))
                    if value:
                        cells.append(value)
                if cells:
                    # Keep a visible cell boundary rather than inventing a
                    # contiguous person's name out of adjacent table cells.
                    yield ' | '.join(cells)


def extract_docx(data: bytes) -> str:
    doc = Document(io.BytesIO(data))
    headers, footers = [], []
    seen_parts = set()
    for section in doc.sections:
        for destination, parts in ((headers, (section.header, section.first_page_header, section.even_page_header)),
                                   (footers, (section.footer, section.first_page_footer, section.even_page_footer))):
            for part in parts:
                # Linked sections share a part. Include its text just once.
                if part._element in seen_parts:
                    continue
                seen_parts.add(part._element)
                destination.extend(_block_text(part))
    text = '\n'.join([*headers, *_block_text(doc), *footers]).strip()
    if not text:
        raise ValueError("No se pudo extraer texto del documento Word.")
    return text
