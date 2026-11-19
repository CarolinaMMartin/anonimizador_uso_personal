"""Análisis de documentos."""
from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.detection.dictionaries import CatalogLoadError
from app.models.schemas import AnalyzeRequest, AnalyzeResponse, CancelRequest
from app.models.store import store
from app.services.analysis_cancel import AnalysisCancelledError, request_cancel
from app.services.analyze import DEFAULT_CATEGORIES, review_response, run_full_analysis

router = APIRouter(prefix="/api", tags=["analyze"])


@router.post("/analyze/cancel")
async def cancel_analyze(req: CancelRequest):
    state = store.get(req.session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    request_cancel(req.session_id)
    return {"cancelled": True, "session_id": req.session_id}


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_document(req: AnalyzeRequest):
    state = store.get(req.session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    if not state.doc_text:
        raise HTTPException(400, "No hay documento cargado")

    if req.enabled_categories == []:
        raise HTTPException(400, "Seleccioná al menos una categoría para analizar.")
    sequence = state.review_sequence
    if sequence > (state.last_analysis_sequence or 0):
        same_settings = (req.label_mode == state.label_mode and
                         set(req.enabled_categories or DEFAULT_CATEGORIES) ==
                         set(state.enabled_categories or DEFAULT_CATEGORIES))
        if state.last_analysis_sequence is not None and same_settings:
            return review_response(state, preserved=True)
        if req.replace_review_sequence != sequence:
            raise HTTPException(409, detail={
                "code": "review_replacement",
                "review_sequence": sequence,
                "message": "El nuevo análisis reemplazará las selecciones, etiquetas y grupos revisados a mano.",
            })

    analyzed_state = state.model_copy(deep=True)
    analyzed_state.label_mode = req.label_mode
    analyzed_state.enabled_categories = req.enabled_categories or []

    try:
        result = await run_in_threadpool(run_full_analysis, analyzed_state)
    except AnalysisCancelledError as e:
        raise HTTPException(409, "Análisis cancelado") from e
    except CatalogLoadError as e:
        raise HTTPException(503, f"No se pudo cargar el catálogo de personas: {e}") from e
    # Check and commit on the event loop, alongside the manual edit handlers.
    if store.get(req.session_id) is not state or state.review_sequence != sequence:
        raise HTTPException(409, "La revisión cambió durante el análisis. Se conservó la revisión más reciente.")
    analyzed_state.last_analysis_sequence = sequence
    analyzed_state.has_review = True
    store.save(analyzed_state)
    return result


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    state = store.get(session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    return {
        "session_id": state.session_id,
        "doc_name": state.doc_name,
        "char_count": len(state.doc_text),
        "detections_count": len(state.detections),
        "clusters_count": len(state.clusters),
        "has_review": state.has_review or bool(state.detections),
    }
