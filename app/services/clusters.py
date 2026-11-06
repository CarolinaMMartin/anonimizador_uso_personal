"""Exclusive group membership and consistent labels through review edits."""
from uuid import uuid4

from app.anonymize.placeholders import make_placeholder, next_placeholder_number
from app.models.schemas import Category, Cluster, Detection, Mention, SessionState
from app.services.review_state import manual_decision, mark_manual_decision


def _cluster_detections(state: SessionState, cluster: Cluster) -> list[Detection]:
    ids = set(cluster.mention_ids)
    return [det for det in state.detections
            if det.cluster_id == cluster.cluster_id or ids.intersection(det.mention_ids)]


def _can_ensure_mentions(state: SessionState, detection: Detection) -> bool:
    return bool(detection.positions) or any(
        mention.id in detection.mention_ids and mention.cat == detection.cat
        for mention in state.mentions
    )


def _ensure_mentions_for_detection(state: SessionState, det: Detection) -> set[str]:
    valid_ids = {mention.id for mention in state.mentions if mention.cat == det.cat}
    ids = set(det.mention_ids) & valid_ids
    if not ids:
        for position in det.positions:
            mid = f'm_manual_{uuid4().hex}'
            state.mentions.append(Mention(
                id=mid, cat=det.cat, surface=position.raw or det.original,
                start=position.start, end=position.end, source_layer='manual',
            ))
            ids.add(mid)
    det.mention_ids = sorted(ids)
    return ids


def _rebuild_cluster_surfaces(state: SessionState, cluster: Cluster) -> None:
    ids = set(cluster.mention_ids)
    members = [mention for mention in state.mentions if mention.id in ids and mention.cat == cluster.cat]
    cluster.mention_ids = [mention.id for mention in members]
    cluster.surfaces = list(dict.fromkeys(mention.surface.strip() for mention in members))


def _sync_cluster_to_detections(state: SessionState, cluster: Cluster) -> None:
    ids = set(cluster.mention_ids)
    for detection in state.detections:
        if detection.cat == cluster.cat and ids.intersection(detection.mention_ids):
            detection.cluster_id = cluster.cluster_id
            detection.cluster_confirmed = cluster.status == 'confirmed'
            if detection.cluster_confirmed and cluster.placeholder:
                detection.placeholder = cluster.placeholder
                detection.manual_placeholder = cluster.manual_placeholder


def _release_detections(state: SessionState, cluster: Cluster, ids: set[str]) -> None:
    for detection in state.detections:
        if detection.cluster_id != cluster.cluster_id or not ids.intersection(detection.mention_ids):
            continue
        detection.cluster_id = None
        detection.cluster_confirmed = False
        if cluster.status == 'confirmed' and detection.placeholder == cluster.placeholder:
            detection.placeholder = make_placeholder(
                detection.cat, detection.original,
                next_placeholder_number(state.detections, detection.cat), state.label_mode,
            )
            detection.manual_placeholder = False


def detach_mentions(state: SessionState, ids: set[str], except_id: str | None = None) -> None:
    """Remove selected mentions from previous owners before assigning new ones."""
    for cluster in list(state.clusters):
        if cluster.cluster_id == except_id or not ids.intersection(cluster.mention_ids):
            continue
        _release_detections(state, cluster, ids)
        cluster.mention_ids = [mid for mid in cluster.mention_ids if mid not in ids]
        _rebuild_cluster_surfaces(state, cluster)
        if not cluster.mention_ids:
            state.clusters.remove(cluster)
        else:
            _sync_cluster_to_detections(state, cluster)


def _selected(state: SessionState, detection_ids: list[int], cat: str | None = None) -> list[Detection]:
    ids = set(detection_ids)
    selected = [det for det in state.detections if det.id in ids]
    if not selected or len(selected) != len(ids):
        return []
    categories = {det.cat for det in selected}
    if len(categories) != 1 or (cat and categories != {cat}):
        return []
    return selected


@manual_decision
def add_detections_to_cluster(
    state: SessionState, cluster_id: str, detection_ids: list[int], reclassify: bool = False,
    *, manual_assignment: bool = True,
) -> Cluster | None:
    cluster = next((c for c in state.clusters if c.cluster_id == cluster_id), None)
    requested = set(detection_ids)
    selected = [det for det in state.detections if det.id in requested]
    if not cluster or not selected or len(selected) != len(requested):
        return None
    if not all(_can_ensure_mentions(state, det) for det in selected):
        return None
    if cluster.target_cluster_id and any(det.cluster_id == cluster.target_cluster_id for det in selected):
        return None
    if any(det.cat != cluster.cat for det in selected):
        if not reclassify:
            return None
        from app.services.detections import update_detection
        for det in selected:
            if det.cat != cluster.cat:
                update_detection(state, det.id, cat=cluster.cat)
    ids = set().union(*(_ensure_mentions_for_detection(state, det) for det in selected))
    if not ids:
        return None
    detach_mentions(state, ids, except_id=cluster_id)
    if manual_assignment:
        for det in selected:
            det.grouping_excluded = False
        if 'manual_assignment' not in cluster.reasons:
            cluster.reasons.append('manual_assignment')
    cluster.mention_ids.extend(sorted(ids - set(cluster.mention_ids)))
    _rebuild_cluster_surfaces(state, cluster)
    _sync_cluster_to_detections(state, cluster)
    if manual_assignment:
        mark_manual_decision(state, _cluster_detections(state, cluster))
    return cluster


@manual_decision
def reclassify_cluster(state: SessionState, cluster_id: str, cat: Category) -> Cluster | None:
    cluster = next((c for c in state.clusters if c.cluster_id == cluster_id), None)
    if not cluster:
        return None
    ids = set(cluster.mention_ids)
    members = _cluster_detections(state, cluster)
    if not members:
        return None
    if cluster.cat == cat:
        mark_manual_decision(state, members)
        return cluster
    placeholder = cluster.placeholder if cluster.manual_placeholder else None
    if cluster.status == 'confirmed' and placeholder is None:
        placeholder = make_placeholder(
            cat, members[0].original, next_placeholder_number(state.detections, cat), state.label_mode,
        )
    for det in members:
        if cluster.status == 'confirmed':
            replacement = placeholder
            manual_placeholder = cluster.manual_placeholder
        else:
            replacement = det.placeholder if det.manual_placeholder else make_placeholder(
                cat, det.original, next_placeholder_number(state.detections, cat), state.label_mode,
            )
            manual_placeholder = det.manual_placeholder
        det.cat = cat
        det.placeholder = replacement
        det.manual_placeholder = manual_placeholder
        ids.update(det.mention_ids)
    for mention in state.mentions:
        if mention.id in ids:
            mention.cat = cat
    cluster.cat = cat
    cluster.target_cluster_id = None
    cluster.placeholder = placeholder
    cluster.canonical_label = placeholder
    cluster.mention_ids = sorted(ids)
    if 'manual_category' not in cluster.reasons:
        cluster.reasons.append('manual_category')
    _rebuild_cluster_surfaces(state, cluster)
    _sync_cluster_to_detections(state, cluster)
    mark_manual_decision(state, members)
    return cluster


@manual_decision
def create_cluster_from_detections(state: SessionState, detection_ids: list[int], cat: str | None = None) -> Cluster | None:
    selected = _selected(state, detection_ids, cat)
    if not selected:
        return None
    if not all(_can_ensure_mentions(state, det) for det in selected):
        return None
    ids = set().union(*(_ensure_mentions_for_detection(state, det) for det in selected))
    if not ids:
        return None
    detach_mentions(state, ids)
    for det in selected:
        det.grouping_excluded = False
    cluster = Cluster(
        cluster_id=f'manual_{uuid4().hex}', cat=selected[0].cat,
        mention_ids=sorted(ids), confidence='media', reasons=['manual'],
    )
    state.clusters.append(cluster)
    _rebuild_cluster_surfaces(state, cluster)
    _sync_cluster_to_detections(state, cluster)
    mark_manual_decision(state, selected)
    return cluster


@manual_decision
def confirm_cluster(state: SessionState, cluster_id: str) -> Cluster | None:
    cluster = next((c for c in state.clusters if c.cluster_id == cluster_id), None)
    if not cluster:
        return None
    if cluster.target_cluster_id:
        target = next((c for c in state.clusters if c.cluster_id == cluster.target_cluster_id), None)
        if not target or target.status != 'confirmed' or target.cat != cluster.cat:
            return None
        return absorb_cluster_into(state, target.cluster_id, cluster_id)
    if not any(mention.id in cluster.mention_ids and mention.cat == cluster.cat for mention in state.mentions):
        return None
    _rebuild_cluster_surfaces(state, cluster)
    cluster.status = 'confirmed'
    cluster.placeholder = cluster.placeholder or make_placeholder(
        cluster.cat, cluster.surfaces[0], next_placeholder_number(state.detections, cluster.cat), state.label_mode,
    )
    cluster.canonical_label = cluster.placeholder
    _sync_cluster_to_detections(state, cluster)
    mark_manual_decision(state, _cluster_detections(state, cluster))
    return cluster


@manual_decision
def split_cluster(state: SessionState, cluster_id: str, mention_ids: list[str]) -> list[Cluster]:
    cluster = next((c for c in state.clusters if c.cluster_id == cluster_id), None)
    if not cluster:
        return []
    ids = set(mention_ids)
    if not ids or not ids.issubset(cluster.mention_ids):
        return []
    affected = _cluster_detections(state, cluster)
    if 'split' not in cluster.reasons:
        cluster.reasons.append('split')
    # A table row has one replacement for all its exact occurrences. Split it
    # atomically so later confirmation cannot put that row in two groups.
    for detection in state.detections:
        if ids.intersection(detection.mention_ids):
            ids.update(set(detection.mention_ids) & set(cluster.mention_ids))
    detach_mentions(state, ids)
    separate = Cluster(
        cluster_id=f'split_{uuid4().hex}', cat=cluster.cat,
        mention_ids=sorted(ids), confidence='media', reasons=['split'],
    )
    state.clusters.append(separate)
    _rebuild_cluster_surfaces(state, separate)
    _sync_cluster_to_detections(state, separate)
    mark_manual_decision(state, affected)
    return [separate]


@manual_decision
def remove_surface_from_cluster(state: SessionState, cluster_id: str, surface: str) -> list[Cluster]:
    from app.resolution.normalize import normalize_text
    cluster = next((c for c in state.clusters if c.cluster_id == cluster_id), None)
    if not cluster:
        return []
    ids = [mention.id for mention in state.mentions
           if mention.id in cluster.mention_ids and normalize_text(mention.surface) == normalize_text(surface)]
    return split_cluster(state, cluster_id, ids)


@manual_decision
def absorb_cluster_into(
    state: SessionState, target_id: str, source_id: str, reclassify: bool = False,
) -> Cluster | None:
    target = next((c for c in state.clusters if c.cluster_id == target_id), None)
    source = next((c for c in state.clusters if c.cluster_id == source_id), None)
    if not target or not source or target_id == source_id or target.target_cluster_id == source_id:
        return None
    if target.cat != source.cat:
        if not reclassify or not reclassify_cluster(state, source_id, target.cat):
            return None
    ids = set(source.mention_ids)
    detach_mentions(state, ids, except_id=target_id)
    target.mention_ids.extend(sorted(ids - set(target.mention_ids)))
    for detection in state.detections:
        if ids.intersection(detection.mention_ids):
            detection.grouping_excluded = False
    if 'manual_merge' not in target.reasons:
        target.reasons.append('manual_merge')
    _rebuild_cluster_surfaces(state, target)
    _sync_cluster_to_detections(state, target)
    mark_manual_decision(state, _cluster_detections(state, target))
    return target


@manual_decision
def merge_clusters(state: SessionState, cluster_ids: list[str]) -> Cluster | None:
    selected = [cluster for cluster in state.clusters if cluster.cluster_id in cluster_ids]
    if len(selected) < 2 or len(selected) != len(set(cluster_ids)) or len({cluster.cat for cluster in selected}) != 1:
        return None
    ids = {mid for cluster in selected for mid in cluster.mention_ids}
    detach_mentions(state, ids)
    merged = Cluster(
        cluster_id=f'merged_{uuid4().hex}', cat=selected[0].cat,
        mention_ids=sorted(ids), confidence='media', reasons=['manual_merge'],
    )
    state.clusters.append(merged)
    _rebuild_cluster_surfaces(state, merged)
    _sync_cluster_to_detections(state, merged)
    mark_manual_decision(state, _cluster_detections(state, merged))
    return merged


@manual_decision
def reject_cluster(state: SessionState, cluster_id: str) -> bool:
    cluster = next((c for c in state.clusters if c.cluster_id == cluster_id), None)
    if not cluster:
        return False
    ids = set(cluster.mention_ids)
    affected = _cluster_detections(state, cluster)
    for detection in state.detections:
        if ids.intersection(detection.mention_ids):
            detection.grouping_excluded = True
    detach_mentions(state, ids)
    mark_manual_decision(state, affected)
    return True
