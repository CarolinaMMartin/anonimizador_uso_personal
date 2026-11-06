"""Orquestación de capas de detección."""
import logging

from app.config import ENABLE_PRESIDIO, ENABLE_SPACY
from app.detection.filters import apply_quality_filters
from app.detection.regex_ar import RawItem, detect_regex_ar
from app.models.schemas import Mention

logger = logging.getLogger(__name__)


def resolve_overlaps(items: list[RawItem], text: str) -> list[RawItem]:
    """Conserva la cobertura completa de las coincidencias ya validadas."""
    priority = {cat: index for index, cat in enumerate((
        "PERSONA", "DNI", "TELEFONO", "PATENTE", "CUIT", "EXPEDIENTE",
        "OTRO", "EMAIL", "DOMICILIO", "ORGANISMO", "EMPRESA",
    ))}
    ordered = sorted(items, key=lambda item: (item.start, -item.end))
    resolved: list[RawItem] = []
    group: list[RawItem] = []
    group_end = -1

    def append_group() -> None:
        if not group:
            return
        representative = max(group, key=lambda item: (
            item.end - item.start, priority.get(item.cat, -1),
            item.source_layer not in {"spacy", "presidio"},
        ))
        start = group[0].start
        resolved.append(RawItem(representative.cat, text[start:group_end],
                                start, group_end, representative.source_layer))

    for item in ordered:
        if not 0 <= item.start < item.end <= len(text):
            raise ValueError("Posición de detección inválida")
        if group and item.start >= group_end:
            append_group()
            group = []
        group.append(item)
        group_end = max(group_end, item.end)
    append_group()
    return resolved


def raw_to_mentions(items: list[RawItem]) -> list[Mention]:
    mentions: list[Mention] = []
    for i, it in enumerate(items):
        mentions.append(
            Mention(
                id=f"m{i}",
                cat=it.cat,  # type: ignore[arg-type]
                surface=it.original,
                start=it.start,
                end=it.end,
                norm=it.original.strip().lower(),
                source_layer=it.source_layer,
            )
        )
    return mentions


def run_detection(
    text: str,
    enabled_categories: list[str] | None = None,
    session_id: str | None = None,
) -> list[Mention]:
    from app.services.analysis_cancel import AnalysisCancelledError, check_cancel

    check_cancel(session_id)
    items = detect_regex_ar(text)

    if ENABLE_PRESIDIO:
        check_cancel(session_id)
        try:
            from app.detection.presidio_layer import detect_presidio

            presidio_items = detect_presidio(text, session_id=session_id)
            items.extend(presidio_items)
            logger.debug("Presidio: %d menciones", len(presidio_items))
        except AnalysisCancelledError:
            raise
        except Exception as e:
            logger.warning("Capa Presidio omitida: %s", e)

    if ENABLE_SPACY:
        check_cancel(session_id)
        try:
            from app.detection.spacy_layer import detect_spacy

            spacy_items = detect_spacy(text, session_id=session_id)
            items.extend(spacy_items)
            logger.debug("spaCy: %d menciones", len(spacy_items))
        except AnalysisCancelledError:
            raise
        except Exception as e:
            logger.warning("Capa spaCy omitida: %s", e)

    check_cancel(session_id)

    items = apply_quality_filters(items, text)
    protected = [item for item in items if item.cat != 'PERSONA']
    if enabled_categories is not None:
        items = [item for item in items if item.cat in enabled_categories]

    if enabled_categories is None or 'PERSONA' in enabled_categories:
        from app.detection.document_aliases import detect_document_aliases

        seeds = [item for item in items if item.cat == 'PERSONA' and not any(
            other.start <= item.start and item.end <= other.end for other in protected)]
        items.extend(detect_document_aliases(text, seeds, protected, session_id))

    return raw_to_mentions(resolve_overlaps(items, text))
