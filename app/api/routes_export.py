"""Exportación de documentos."""
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.anonymize.apply import anonymize_text
from app.export.csv_export import build_csv_bytes
from app.export.docx_export import build_docx_bytes
from app.export.export_utils import (
    format_from_options,
    resolve_export_text,
    text_to_paragraphs,
)
from app.export.http_headers import content_disposition_attachment
from app.export.pdf_export import build_pdf_bytes
from app.models.schemas import (
    AnonymizedPreviewResponse,
    ExportDocumentRequest,
    ExportRequest,
)
from app.models.store import store
from app.services.analyze import _prune_detections

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["export"])


def _anonymized_preview_text(state, use_confirmed_only: bool = False) -> str:
    detections = _prune_detections(state.detections, state.doc_text)
    return anonymize_text(
        state.doc_text, detections, confirmed_only=use_confirmed_only
    )


@router.post("/export/preview", response_model=AnonymizedPreviewResponse)
async def export_preview(req: ExportRequest):
    state = store.get(req.session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    if not state.detections:
        raise HTTPException(400, "No hay detecciones. Analizá el documento primero.")
    try:
        text = _anonymized_preview_text(state, req.use_confirmed_only)
        return AnonymizedPreviewResponse(
            session_id=state.session_id,
            doc_name=state.doc_name,
            text=text,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generando vista previa anonimizada")
        raise HTTPException(500, f"Error al preparar texto: {e}") from e


@router.post("/export/docx")
async def export_docx(req: ExportDocumentRequest):
    state = store.get(req.session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    if not state.detections:
        raise HTTPException(400, "No hay detecciones. Analizá el documento primero.")

    try:
        anon = resolve_export_text(state, req)
        store.save(state)
        fmt = format_from_options(req.format)
        paragraphs = text_to_paragraphs(anon)
        data = build_docx_bytes(paragraphs, fmt)
        filename = f"{state.doc_name}_anonimizado.docx"
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": content_disposition_attachment(filename)},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error exportando DOCX")
        raise HTTPException(500, f"Error al generar Word: {e}") from e


@router.post("/export/pdf")
async def export_pdf(req: ExportDocumentRequest):
    state = store.get(req.session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    if not state.detections:
        raise HTTPException(400, "No hay detecciones. Analizá el documento primero.")

    try:
        anon = resolve_export_text(state, req)
        store.save(state)
        fmt = format_from_options(req.format)
        paragraphs = text_to_paragraphs(anon)
        data = build_pdf_bytes(paragraphs, fmt)
        filename = f"{state.doc_name}_anonimizado.pdf"
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Content-Disposition": content_disposition_attachment(filename)},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error exportando PDF")
        raise HTTPException(500, f"Error al generar PDF: {e}") from e


@router.post("/export/csv")
async def export_csv(req: ExportRequest):
    state = store.get(req.session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    if not state.detections:
        raise HTTPException(400, "No hay detecciones")

    try:
        detections = _prune_detections(state.detections, state.doc_text)
        data = build_csv_bytes(detections)
        filename = f"{state.doc_name}_equivalencias.csv"
        return Response(
            content=data,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": content_disposition_attachment(filename)},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error exportando CSV")
        raise HTTPException(500, f"Error al generar CSV: {e}") from e
