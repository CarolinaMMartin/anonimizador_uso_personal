"""Gestión de clusters / identidades."""
from fastapi import APIRouter, HTTPException

from app.anonymize.apply import anonymize_text, build_highlights
from app.models.schemas import (
    ClusterAddDetectionsRequest,
    ClusterCreateRequest,
    ClusterAbsorbRequest,
    ClusterMergeRequest,
    ClusterRemoveSurfaceRequest,
    ClusterSplitRequest,
    ClusterUpdateRequest,
    ConfirmResponse,
)
from app.models.store import store
from app.services.clusters import (
    add_detections_to_cluster,
    confirm_cluster,
    create_cluster_from_detections,
    absorb_cluster_into,
    merge_clusters,
    remove_surface_from_cluster,
    split_cluster,
)

router = APIRouter(prefix="/api", tags=["entities"])


# Rutas estáticas primero (evitan ambigüedad con {cluster_id})
@router.post("/clusters/create")
async def create_cluster_endpoint(session_id: str, body: ClusterCreateRequest):
    state = store.get(session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    cluster = create_cluster_from_detections(
        state, body.detection_ids, body.cat
    )
    if not cluster:
        raise HTTPException(400, "No se pudo crear el grupo")
    store.save(state)
    return {"cluster": cluster, "clusters": state.clusters, "detections": state.detections}


@router.post("/clusters/merge")
async def merge_clusters_endpoint(session_id: str, body: ClusterMergeRequest):
    state = store.get(session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    merged = merge_clusters(state, body.cluster_ids)
    if not merged:
        raise HTTPException(400, "Se requieren al menos 2 clusters")
    store.save(state)
    return {"cluster": merged, "clusters": state.clusters}


@router.get("/clusters")
async def list_clusters(session_id: str):
    state = store.get(session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    return {"clusters": state.clusters, "detections": state.detections}


@router.post("/clusters/{cluster_id}/confirm", response_model=ConfirmResponse)
async def confirm_cluster_endpoint(cluster_id: str, session_id: str):
    state = store.get(session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    cluster = confirm_cluster(state, cluster_id)
    if not cluster:
        raise HTTPException(404, "Cluster no encontrado")
    store.save(state)
    return ConfirmResponse(cluster=cluster, detections=state.detections)


@router.post("/clusters/{cluster_id}/split")
async def split_cluster_endpoint(
    cluster_id: str, session_id: str, body: ClusterSplitRequest
):
    state = store.get(session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    new_clusters = split_cluster(state, cluster_id, body.mention_ids)
    store.save(state)
    return {"clusters": state.clusters, "new_clusters": new_clusters}


@router.post("/clusters/{cluster_id}/remove-surface")
async def remove_surface_endpoint(
    cluster_id: str, session_id: str, body: ClusterRemoveSurfaceRequest
):
    state = store.get(session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    new_clusters = remove_surface_from_cluster(state, cluster_id, body.surface)
    if not new_clusters:
        raise HTTPException(400, "No se pudo quitar la variante del grupo")
    store.save(state)
    return {"clusters": state.clusters, "detections": state.detections}


@router.post("/clusters/{target_id}/absorb")
async def absorb_cluster_endpoint(
    target_id: str, session_id: str, body: ClusterAbsorbRequest
):
    """Une un grupo sugerido dentro de otro (p. ej. M. A. Benitez → Marcos Benítez)."""
    state = store.get(session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    cluster = absorb_cluster_into(state, target_id, body.source_cluster_id)
    if not cluster:
        raise HTTPException(400, "No se pudo unir el grupo")
    store.save(state)
    return {
        "cluster": cluster,
        "clusters": state.clusters,
        "detections": state.detections,
    }


@router.post("/clusters/{cluster_id}/add")
async def add_to_cluster_endpoint(
    cluster_id: str, session_id: str, body: ClusterAddDetectionsRequest
):
    state = store.get(session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    cluster = add_detections_to_cluster(state, cluster_id, body.detection_ids)
    if not cluster:
        raise HTTPException(404, "Cluster no encontrado o detección inválida")
    store.save(state)
    return {"cluster": cluster, "clusters": state.clusters, "detections": state.detections}


@router.patch("/clusters/{cluster_id}")
async def update_cluster(
    cluster_id: str, session_id: str, body: ClusterUpdateRequest
):
    state = store.get(session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    cluster = next((c for c in state.clusters if c.cluster_id == cluster_id), None)
    if not cluster:
        raise HTTPException(404, "Cluster no encontrado")
    if body.placeholder:
        cluster.placeholder = body.placeholder
        if cluster.status == "confirmed":
            for d in state.detections:
                if d.cluster_id == cluster_id:
                    d.placeholder = body.placeholder
    if body.canonical_label:
        cluster.canonical_label = body.canonical_label
    store.save(state)
    return {"cluster": cluster}


@router.get("/preview")
async def preview_text(session_id: str, mode: str = "orig"):
    state = store.get(session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    if mode == "anon":
        text = anonymize_text(state.doc_text, state.detections, confirmed_only=False)
    else:
        text = state.doc_text
    highlights = build_highlights(state.doc_text, state.detections)
    return {"text": text, "highlights": highlights, "mode": mode}
