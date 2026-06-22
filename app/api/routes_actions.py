"""Rutas simplificadas (sin parámetros en path) para evitar 404 en el cliente."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.schemas import Category
from app.models.store import store
from app.services.clusters import add_detections_to_cluster, create_cluster_from_detections
from app.services.detections import add_manual_detection

router = APIRouter(prefix="/api", tags=["actions"])


class AssignClusterBody(BaseModel):
    session_id: str
    detection_id: int
    cluster_id: str  # id existente o "__new__"


class ManualDetectionBody(BaseModel):
    session_id: str
    cat: Category
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    original: str | None = None


@router.post("/assign-cluster")
async def assign_cluster(body: AssignClusterBody):
    state = store.get(body.session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada. Volvé a cargar el documento.")

    if body.cluster_id == "__new__":
        cluster = create_cluster_from_detections(state, [body.detection_id])
    else:
        cluster = add_detections_to_cluster(
            state, body.cluster_id, [body.detection_id]
        )
    if not cluster:
        raise HTTPException(
            400,
            "No se pudo asignar al grupo. Probá crear un grupo nuevo.",
        )
    store.save(state)
    return {
        "cluster": cluster,
        "clusters": state.clusters,
        "detections": state.detections,
    }


@router.post("/manual-detection")
async def manual_detection(body: ManualDetectionBody):
    state = store.get(body.session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada. Volvé a cargar el documento.")
    if not state.doc_text:
        raise HTTPException(400, "No hay documento cargado")
    try:
        det = add_manual_detection(
            state, body.cat, body.start, body.end, body.original
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    store.save(state)
    return {"detection": det, "detections": state.detections}
