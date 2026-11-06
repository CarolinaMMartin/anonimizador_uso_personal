"""Servicio de análisis completo."""
import logging
import time

from app.detection.pipeline import run_detection
from app.models.schemas import AnalyzeResponse, SessionState
from app.resolution.cluster import build_clusters, mentions_to_detections
from app.services.analysis_cancel import check_cancel, clear_cancel

logger = logging.getLogger(__name__)


DEFAULT_CATEGORIES = [
    "PERSONA",
    "DNI",
    "CUIT",
    "EMPRESA",
    "EMAIL",
    "TELEFONO",
    "DOMICILIO",
    "PATENTE",
    "EXPEDIENTE",
    "ORGANISMO",
    "OTRO",
]


def run_full_analysis(state: SessionState) -> AnalyzeResponse:
    clear_cancel(state.session_id)
    cats = state.enabled_categories or DEFAULT_CATEGORIES
    t0 = time.perf_counter()
    mentions = run_detection(
        state.doc_text, enabled_categories=cats, session_id=state.session_id
    )
    t1 = time.perf_counter()
    check_cancel(state.session_id)
    state.mentions = mentions
    clusters = build_clusters(mentions, state.doc_text)
    t2 = time.perf_counter()
    check_cancel(state.session_id)
    logger.info(
        "Análisis %s: detección %.1fs (%d menciones), clustering %.1fs (%d grupos), total %.1fs",
        state.doc_name or state.session_id,
        t1 - t0,
        len(mentions),
        t2 - t1,
        len(clusters),
        t2 - t0,
    )
    state.clusters = clusters
    detections = mentions_to_detections(mentions, state.label_mode, clusters)
    state.detections = detections

    stats: dict[str, int] = {c: 0 for c in DEFAULT_CATEGORIES}
    stats["TOTAL"] = len(detections)
    for d in detections:
        if d.enabled and d.cat in stats:
            stats[d.cat] += 1

    return AnalyzeResponse(
        session_id=state.session_id,
        detections=detections,
        clusters=clusters,
        stats=stats,
    )
