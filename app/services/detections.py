"""Alta y baja manual de detecciones."""
import re

from app.anonymize.placeholders import make_placeholder
from app.models.schemas import Category, Detection, Mention, Position, SessionState


def _next_mention_id(state: SessionState) -> str:
    n = len(state.mentions)
    return f"m_manual_{n}"


def _find_positions(text: str, surface: str) -> list[Position]:
    escaped = re.escape(surface.strip())
    positions: list[Position] = []
    for m in re.finditer(escaped, text, re.IGNORECASE):
        positions.append(Position(start=m.start(), end=m.end(), raw=text[m.start() : m.end()]))
    return positions


def add_manual_detection(
    state: SessionState,
    cat: str,
    start: int,
    end: int,
    original: str | None = None,
) -> Detection:
    """Agrega una detección manual (p. ej. texto seleccionado en vista previa)."""
    text = state.doc_text
    if start < 0 or end > len(text) or end <= start:
        raise ValueError("Rango de texto inválido")

    surface = (original or text[start:end]).strip()
    if len(surface) < 2:
        raise ValueError("Selección demasiado corta")

    from app.detection.filters import is_valid_manual_detection

    if not is_valid_manual_detection(cat, surface, text, start):
        raise ValueError(
            "Esa selección no parece un dato personal válido (frase o cita procesal). "
            "Probá con un nombre, DNI, domicilio, etc."
        )

    if text[start:end].strip().lower() != surface.lower():
        # Re-sincronizar con el documento
        chunk = text[start:end].strip()
        if chunk:
            surface = chunk

    # Todas las ocurrencias iguales (como v1)
    positions = _find_positions(text, surface)
    if not positions:
        positions = [Position(start=start, end=end, raw=text[start:end])]

    mention = Mention(
        id=_next_mention_id(state),
        cat=cat,  # type: ignore[arg-type]
        surface=surface,
        start=positions[0].start,
        end=positions[0].end,
        norm=surface.lower(),
        source_layer="manual",
    )
    state.mentions.append(mention)

    key = f"{cat}||{surface.lower()}"
    existing = next(
        (
            d
            for d in state.detections
            if f"{d.cat}||{d.original.strip().lower()}" == key
        ),
        None,
    )
    if existing:
        seen = {(p.start, p.end) for p in existing.positions}
        for p in positions:
            if (p.start, p.end) not in seen:
                existing.positions.append(p)
                seen.add((p.start, p.end))
        existing.mention_ids.append(mention.id)
        return existing

    counters: dict[str, int] = {}
    for d in state.detections:
        counters[d.cat] = counters.get(d.cat, 0) + 1
    counters[cat] = counters.get(cat, 0) + 1
    new_id = max((d.id for d in state.detections), default=-1) + 1
    det = Detection(
        id=new_id,
        cat=cat,  # type: ignore[arg-type]
        original=surface,
        placeholder=make_placeholder(cat, surface, counters[cat], state.label_mode),
        enabled=True,
        positions=positions,
        mention_ids=[mention.id],
        user_added=True,
    )
    state.detections.append(det)
    return det


def add_bulk_detection(
    state: SessionState,
    cat: Category,
    original: str,
    positions: list[Position],
    placeholder: str | None = None,
) -> Detection:
    """Crea (o extiende) una detección a partir de posiciones ya calculadas.

    Uso previsto: buscador del preview. El frontend hizo el matching
    (insensible a acentos y a mayúsculas) sobre el texto del documento y
    envía la lista completa de posiciones. Acá validamos, deduplicamos y
    aplicamos la misma regla de "extender si ya existe una detección con
    misma cat+original" que `add_manual_detection`.

    A diferencia de `add_manual_detection`, no aplica el filtro
    `is_valid_manual_detection`: cuando la persona escribe explícitamente
    en el buscador ya declaró intención; ese filtro está pensado para
    selecciones accidentales con el mouse.
    """
    text = state.doc_text
    surface = original.strip()
    if len(surface) < 2:
        raise ValueError("El texto a anonimizar es demasiado corto (mínimo 2 caracteres)")

    if not positions:
        raise ValueError("No se recibieron coincidencias para anonimizar")

    # Validar y deduplicar posiciones
    seen: set[tuple[int, int]] = set()
    clean_positions: list[Position] = []
    for p in positions:
        if p.start < 0 or p.end > len(text) or p.end <= p.start:
            raise ValueError(f"Rango de texto inválido: {p.start}-{p.end}")
        key = (p.start, p.end)
        if key in seen:
            continue
        seen.add(key)
        clean_positions.append(
            Position(start=p.start, end=p.end, raw=text[p.start : p.end])
        )

    mention = Mention(
        id=_next_mention_id(state),
        cat=cat,
        surface=surface,
        start=clean_positions[0].start,
        end=clean_positions[0].end,
        norm=surface.lower(),
        source_layer="manual",
    )
    state.mentions.append(mention)

    key = f"{cat}||{surface.lower()}"
    existing = next(
        (
            d
            for d in state.detections
            if f"{d.cat}||{d.original.strip().lower()}" == key
        ),
        None,
    )
    if existing:
        existing_keys = {(p.start, p.end) for p in existing.positions}
        for p in clean_positions:
            if (p.start, p.end) not in existing_keys:
                existing.positions.append(p)
                existing_keys.add((p.start, p.end))
        existing.mention_ids.append(mention.id)
        if placeholder is not None:
            clean = placeholder.strip()
            if not clean:
                raise ValueError("La sustitución no puede estar vacía")
            existing.placeholder = clean
            existing.manual_placeholder = True
        return existing

    counters: dict[str, int] = {}
    for d in state.detections:
        counters[d.cat] = counters.get(d.cat, 0) + 1
    counters[cat] = counters.get(cat, 0) + 1
    new_id = max((d.id for d in state.detections), default=-1) + 1

    if placeholder is not None:
        clean = placeholder.strip()
        if not clean:
            raise ValueError("La sustitución no puede estar vacía")
        final_placeholder = clean
        manual_ph = True
    else:
        final_placeholder = make_placeholder(cat, surface, counters[cat], state.label_mode)
        manual_ph = False

    det = Detection(
        id=new_id,
        cat=cat,
        original=surface,
        placeholder=final_placeholder,
        enabled=True,
        positions=clean_positions,
        mention_ids=[mention.id],
        manual_placeholder=manual_ph,
        user_added=True,
    )
    state.detections.append(det)
    return det


def remove_detection(state: SessionState, detection_id: int) -> None:
    det = next((d for d in state.detections if d.id == detection_id), None)
    if not det:
        raise ValueError("Detección no encontrada")
    mids = set(det.mention_ids)
    state.mentions = [m for m in state.mentions if m.id not in mids]
    state.detections = [d for d in state.detections if d.id != detection_id]
    for i, d in enumerate(state.detections):
        d.id = i
    for c in state.clusters:
        if det.cluster_id and c.cluster_id == det.cluster_id:
            c.surfaces = [s for s in c.surfaces if s.strip().lower() != det.original.strip().lower()]
            c.mention_ids = [mid for mid in c.mention_ids if mid not in mids]


def update_detection(
    state: SessionState,
    detection_id: int,
    cat: str | None = None,
    placeholder: str | None = None,
    enabled: bool | None = None,
) -> Detection:
    det = next((d for d in state.detections if d.id == detection_id), None)
    if not det:
        raise ValueError("Detección no encontrada")

    if cat and cat != det.cat:
        det.cat = cat  # type: ignore[assignment]
        det.cluster_id = None
        for mid in det.mention_ids:
            mention = next((m for m in state.mentions if m.id == mid), None)
            if mention:
                mention.cat = cat  # type: ignore[assignment]
        if placeholder is None or not det.manual_placeholder:
            same_cat_count = sum(1 for d in state.detections if d.cat == cat)
            det.placeholder = make_placeholder(cat, det.original, same_cat_count, state.label_mode)
            det.manual_placeholder = False

    if placeholder is not None:
        clean = placeholder.strip()
        if not clean:
            raise ValueError("La sustitución no puede estar vacía")
        det.placeholder = clean
        det.manual_placeholder = True

    if enabled is not None:
        det.enabled = enabled

    return det
