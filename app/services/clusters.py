"""Operaciones sobre clusters."""
from app.anonymize.placeholders import make_placeholder
from app.models.schemas import Cluster, Detection, Mention, Position, SessionState


def _surfaces_for_mentions(state: SessionState, mention_ids: set[str]) -> list[str]:
    surfaces: list[str] = []
    for m in state.mentions:
        if m.id in mention_ids:
            s = m.surface.strip()
            if s and s not in surfaces:
                surfaces.append(s)
    return surfaces


def _mention_ids_for_detections(
    state: SessionState, detection_ids: list[int]
) -> set[str]:
    ids: set[str] = set()
    for det_id in detection_ids:
        det = next((d for d in state.detections if d.id == det_id), None)
        if not det:
            continue
        if det.mention_ids:
            ids.update(det.mention_ids)
        norm = det.original.strip().lower()
        for m in state.mentions:
            if m.cat != det.cat and det.cat != "PERSONA":
                continue
            if m.surface.strip().lower() == norm:
                ids.add(m.id)
                continue
            for p in det.positions:
                if m.start == p.start and m.end == p.end:
                    ids.add(m.id)
    return ids


def _ensure_mentions_for_detection(
    state: SessionState, det: Detection
) -> set[str]:
    """Crea menciones en estado si la detección no las tiene (evita 404 al agrupar)."""
    ids = _mention_ids_for_detections(state, [det.id])
    if ids:
        det.mention_ids = list(ids)
        return ids

    new_ids: set[str] = set()
    for i, pos in enumerate(det.positions):
        mid = f"m_manual_{det.id}_{i}_{len(state.mentions)}"
        surface = (pos.raw or det.original).strip()
        mention = Mention(
            id=mid,
            cat=det.cat,  # type: ignore[arg-type]
            surface=surface,
            start=pos.start,
            end=pos.end,
            norm=surface.lower(),
            source_layer="manual",
        )
        state.mentions.append(mention)
        new_ids.add(mid)

    if not new_ids and det.original:
        mid = f"m_manual_{det.id}_{len(state.mentions)}"
        pos = det.positions[0] if det.positions else Position(start=0, end=len(det.original))
        mention = Mention(
            id=mid,
            cat=det.cat,  # type: ignore[arg-type]
            surface=det.original.strip(),
            start=pos.start,
            end=pos.end,
            norm=det.original.strip().lower(),
            source_layer="manual",
        )
        state.mentions.append(mention)
        new_ids.add(mid)

    det.mention_ids = list(new_ids)
    return new_ids


def _sync_cluster_to_detections(state: SessionState, cluster: Cluster) -> None:
    """Aplica placeholder del cluster a todas sus detecciones."""
    surfaces = set(cluster.surfaces)
    ph = cluster.placeholder or cluster.canonical_label
    if not ph:
        return
    for d in state.detections:
        if d.original.strip() in surfaces or any(
            mid in cluster.mention_ids for mid in d.mention_ids
        ):
            d.cluster_id = cluster.cluster_id
            if cluster.status == "confirmed":
                d.placeholder = ph
                d.enabled = True


def _rebuild_cluster_surfaces(state: SessionState, cluster: Cluster) -> None:
    cluster.mention_ids = list(dict.fromkeys(cluster.mention_ids))
    cluster.surfaces = _surfaces_for_mentions(state, set(cluster.mention_ids))


def add_detections_to_cluster(
    state: SessionState, cluster_id: str, detection_ids: list[int]
) -> Cluster | None:
    cluster = next((c for c in state.clusters if c.cluster_id == cluster_id), None)
    if not cluster:
        return None

    new_mids: set[str] = set()
    for det_id in detection_ids:
        det = next((d for d in state.detections if d.id == det_id), None)
        if not det:
            continue
        new_mids.update(_ensure_mentions_for_detection(state, det))
    if not new_mids:
        return None

    for mid in new_mids:
        if mid not in cluster.mention_ids:
            cluster.mention_ids.append(mid)

    _rebuild_cluster_surfaces(state, cluster)
    _sync_cluster_to_detections(state, cluster)
    return cluster


def create_cluster_from_detections(
    state: SessionState, detection_ids: list[int], cat: str | None = None
) -> Cluster | None:
    mids: set[str] = set()
    for det_id in detection_ids:
        det = next((d for d in state.detections if d.id == det_id), None)
        if det:
            mids.update(_ensure_mentions_for_detection(state, det))
    if not mids:
        return None
    mids = list(mids)

    d0 = next((d for d in state.detections if d.id == detection_ids[0]), None)
    cluster_cat = cat or (d0.cat if d0 else "PERSONA")

    cluster = Cluster(
        cluster_id=f"manual_{len(state.clusters)}",
        cat=cluster_cat,  # type: ignore[arg-type]
        mention_ids=mids,
        surfaces=_surfaces_for_mentions(state, set(mids)),
        confidence="media",
        status="suggested",
        reasons=["manual"],
    )
    state.clusters.append(cluster)
    _sync_cluster_to_detections(state, cluster)
    return cluster


def confirm_cluster(state: SessionState, cluster_id: str) -> Cluster | None:
    cluster = next((c for c in state.clusters if c.cluster_id == cluster_id), None)
    if not cluster:
        return None

    _rebuild_cluster_surfaces(state, cluster)
    cluster.status = "confirmed"

    counters: dict[str, int] = {}
    for d in state.detections:
        if d.cluster_id and d.placeholder:
            try:
                num = int(d.placeholder.split("_")[-1].strip("]"))
                counters[d.cat] = max(counters.get(d.cat, 0), num)
            except ValueError:
                pass

    counters[cluster.cat] = counters.get(cluster.cat, 0) + 1
    placeholder = cluster.placeholder or make_placeholder(
        cluster.cat,
        cluster.surfaces[0] if cluster.surfaces else "?",
        counters[cluster.cat],
        state.label_mode,
    )
    cluster.placeholder = placeholder
    cluster.canonical_label = placeholder
    _sync_cluster_to_detections(state, cluster)
    return cluster


def split_cluster(
    state: SessionState, cluster_id: str, mention_ids: list[str]
) -> list[Cluster]:
    cluster = next((c for c in state.clusters if c.cluster_id == cluster_id), None)
    if not cluster:
        return []

    keep = [mid for mid in cluster.mention_ids if mid not in mention_ids]
    split_off = mention_ids
    new_clusters: list[Cluster] = []

    if keep:
        cluster.mention_ids = keep
        _rebuild_cluster_surfaces(state, cluster)
        cluster.status = "suggested"
        cluster.placeholder = None
        cluster.canonical_label = None

    if split_off:
        new_id = f"{cluster_id}_split_{len(state.clusters)}"
        nc = Cluster(
            cluster_id=new_id,
            cat=cluster.cat,
            mention_ids=split_off,
            surfaces=_surfaces_for_mentions(state, set(split_off)),
            confidence=cluster.confidence,
            status="suggested",
            reasons=["split"],
        )
        state.clusters.append(nc)
        new_clusters.append(nc)

    return new_clusters


def remove_surface_from_cluster(
    state: SessionState, cluster_id: str, surface: str
) -> list[Cluster]:
    """Saca una variante (texto) de un grupo y la deja como grupo aparte.

    Útil cuando la unificación juntó dos personas distintas con el mismo
    apellido (ej. Sandra y Cristian Villarreal): la variante quitada se
    separa en su propio grupo sugerido para seguir anonimizándose.
    """
    cluster = next((c for c in state.clusters if c.cluster_id == cluster_id), None)
    if not cluster:
        return []

    target = surface.strip().lower()
    move_ids = [
        m.id
        for m in state.mentions
        if m.id in cluster.mention_ids and m.surface.strip().lower() == target
    ]
    if not move_ids:
        return []

    # Soltar las detecciones afectadas del grupo actual.
    for d in state.detections:
        if d.cluster_id == cluster_id and d.original.strip().lower() == target:
            d.cluster_id = None

    return split_cluster(state, cluster_id, move_ids)


def absorb_cluster_into(
    state: SessionState, target_id: str, source_id: str
) -> Cluster | None:
    """Fusiona source dentro de target (conserva id y placeholder del target)."""
    if target_id == source_id:
        return None
    target = next((c for c in state.clusters if c.cluster_id == target_id), None)
    source = next((c for c in state.clusters if c.cluster_id == source_id), None)
    if not target or not source:
        return None

    for mid in source.mention_ids:
        if mid not in target.mention_ids:
            target.mention_ids.append(mid)

    for d in state.detections:
        if d.cluster_id == source_id:
            d.cluster_id = target_id

    state.clusters = [c for c in state.clusters if c.cluster_id != source_id]
    _rebuild_cluster_surfaces(state, target)
    _sync_cluster_to_detections(state, target)
    return target


def merge_clusters(state: SessionState, cluster_ids: list[str]) -> Cluster | None:
    to_merge = [c for c in state.clusters if c.cluster_id in cluster_ids]
    if len(to_merge) < 2:
        return None

    all_ids: list[str] = []
    all_surfaces: list[str] = []
    reasons: list[str] = []
    for c in to_merge:
        all_ids.extend(c.mention_ids)
        all_surfaces.extend(c.surfaces)
        reasons.extend(c.reasons)

    cat = to_merge[0].cat
    merged = Cluster(
        cluster_id=f"merged_{len(state.clusters)}",
        cat=cat,
        mention_ids=list(dict.fromkeys(all_ids)),
        surfaces=list(dict.fromkeys(all_surfaces)),
        confidence="media",
        status="suggested",
        reasons=list(set(reasons)),
    )

    for cid in cluster_ids:
        state.clusters = [c for c in state.clusters if c.cluster_id != cid]
    state.clusters.append(merged)
    _sync_cluster_to_detections(state, merged)
    return merged
