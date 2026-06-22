"""Utilidades compartidas para exportación."""
from __future__ import annotations

from app.anonymize.apply import anonymize_text
from app.export.docx_format import DEFAULT_DOCX_FORMAT, DocxExportFormat
from app.models.schemas import ExportDocumentRequest, ExportFormatOptions, SessionState
from app.services.analyze import _prune_detections


def format_from_options(opts: ExportFormatOptions | None) -> DocxExportFormat:
    if not opts:
        return DEFAULT_DOCX_FORMAT
    return DocxExportFormat(
        font_name=opts.font_name,
        font_size_pt=opts.font_size_pt,
        line_spacing=opts.line_spacing,
        margin_cm=opts.margin_cm,
        margin_top_bottom_cm=opts.margin_top_bottom_cm,
        alignment=opts.alignment,
    )


def resolve_export_text(state: SessionState, req: ExportDocumentRequest) -> str:
    if req.text is not None:
        return req.text
    detections = _prune_detections(state.detections, state.doc_text)
    return anonymize_text(
        state.doc_text, detections, confirmed_only=req.use_confirmed_only
    )


def text_to_paragraphs(text: str) -> list[str]:
    """Convierte texto a párrafos para export (respeta doble salto; une líneas sueltas)."""
    from app.extraction.pdf_cleanup import merge_lines_to_paragraphs

    normalized = merge_lines_to_paragraphs(text.replace("\r\n", "\n"))
    parts = [p.strip() for p in normalized.split("\n\n") if p.strip()]
    if parts:
        return parts
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    return lines or [text.strip() or "(documento vacío)"]
