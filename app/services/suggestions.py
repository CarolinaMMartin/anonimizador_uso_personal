"""Actualiza propuestas sin reemplazar las decisiones de revisión."""
from uuid import uuid4

from app.models.schemas import Cluster, SessionState
from app.resolution.cluster import build_clusters
from app.services.clusters import _ensure_mentions_for_detection


def _reviewed(cluster: Cluster) -> bool:
    return cluster.status == 'confirmed' or any(
        reason == 'split' or reason.startswith('manual') for reason in cluster.reasons
    )


def refresh_suggestions(state: SessionState) -> None:
    preserved = [cluster for cluster in state.clusters if _reviewed(cluster)]
    for cluster in preserved:
        if cluster.target_cluster_id:
            target = next((c for c in state.clusters if c.cluster_id == cluster.target_cluster_id), None)
            if not target or target.status != 'confirmed' or target.cat != cluster.cat:
                cluster.target_cluster_id = None
    protected_ids = {cluster.cluster_id for cluster in preserved}
    owners = {mid: cluster for cluster in preserved for mid in cluster.mention_ids}
    eligible = [det for det in state.detections if det.enabled and not det.grouping_excluded]
    current_ids = set()
    for detection in eligible:
        current_ids.update(_ensure_mentions_for_detection(state, detection))
    mentions = [mention for mention in state.mentions if mention.id in current_ids]
    mention_map = {mention.id: mention for mention in mentions}
    proposed = build_clusters(mentions, state.doc_text)
    previous = [cluster for cluster in state.clusters if cluster.cluster_id not in protected_ids]
    used = set(protected_ids)
    refreshed = []
    for candidate in proposed:
        ids = [mid for mid in candidate.mention_ids if mid not in owners]
        targets = {owners[mid].cluster_id for mid in candidate.mention_ids if mid in owners}
        if not ids or len(targets) > 1:
            continue
        target = next((cluster for cluster in preserved if cluster.cluster_id in targets), None)
        if target and target.status != 'confirmed':
            continue
        if not target and len(ids) < 2:
            continue
        target_id = target.cluster_id if target else None
        matches = [cluster for cluster in previous
                   if cluster.cluster_id not in used and cluster.cat == candidate.cat
                   and cluster.target_cluster_id == target_id
                   and set(ids).intersection(cluster.mention_ids)]
        matches.sort(key=lambda cluster: (-len(set(ids).intersection(cluster.mention_ids)), cluster.cluster_id))
        cluster_id = matches[0].cluster_id if matches else f'sug_{uuid4().hex}'
        used.add(cluster_id)
        refreshed.append(Cluster(
            cluster_id=cluster_id, cat=candidate.cat, mention_ids=ids,
            surfaces=list(dict.fromkeys(mention_map[mid].surface.strip() for mid in ids)),
            confidence=candidate.confidence, reasons=candidate.reasons,
            target_cluster_id=target_id,
        ))
    suggestion_owners = {mid: cluster.cluster_id for cluster in refreshed for mid in cluster.mention_ids}
    for detection in state.detections:
        if detection.cluster_id in protected_ids:
            continue
        groups = {suggestion_owners[mid] for mid in detection.mention_ids if mid in suggestion_owners}
        detection.cluster_id = next(iter(groups)) if len(groups) == 1 else None
        detection.cluster_confirmed = False
    state.clusters = preserved + refreshed
