"""Servicio de análisis completo."""
import logging
import time

from app.detection.pipeline import run_detection
from app.models.schemas import AnalyzeResponse, SessionState
from app.resolution.cluster import build_clusters, mentions_to_detections
from app.services.analysis_cancel import check_cancel, clear_cancel

logger = logging.getLogger(__name__)


def _prune_detections(detections, text: str):
    from app.detection.filters import is_valid_detection

    pruned = []
    for d in detections:
        # Export preparation must not mutate the live session or renumber IDs.
        d = d.model_copy(deep=True)
        if d.user_added or d.cluster_confirmed or 'document_alias' in d.source_layers:
            pruned.append(d)
            continue
        if is_valid_detection(d.cat, d.original, text, d.positions[0].start if d.positions else 0):
            pruned.append(d)
    pruned = _drop_substring_personas(pruned)
    return pruned


def _drop_substring_personas(detections):
    """Quita únicamente posiciones cubiertas por una mención personal mayor."""
    personas = [d for d in detections if d.cat == "PERSONA"]
    otros = [d for d in detections if d.cat != "PERSONA"]
    personas.sort(key=lambda d: len(d.original), reverse=True)
    kept: list = []
    kept_norm: list[str] = []
    for d in personas:
        if getattr(d, "user_added", False):
            kept.append(d)
            kept_norm.append(d.original.strip().lower())
            continue
        low = d.original.strip().lower()
        if any(low != k and low in k for k in kept_norm):
            # A surname mentioned elsewhere is still personal data. Drop only
            # occurrences already covered by another detection, never the row
            # just because its text is a substring of a longer person's name.
            positions = [p for p in d.positions if not any(
                other.start <= p.start and p.end <= other.end
                for existing in kept for other in existing.positions
            )]
            if not positions:
                continue
            d.positions = positions
        kept.append(d)
        kept_norm.append(low)
    return otros + kept


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
    detections = _prune_detections(detections, state.doc_text)
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
