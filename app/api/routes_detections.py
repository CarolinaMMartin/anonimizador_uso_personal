"""Rutas para detecciones manuales."""
from fastapi import APIRouter, HTTPException

from app.models.schemas import Category, Detection
from app.models.store import store
from pydantic import BaseModel, Field

from app.services.detections import add_manual_detection, remove_detection, update_detection

router = APIRouter(prefix="/api/detections", tags=["detections"])


class ManualDetectionRequest(BaseModel):
    session_id: str
    cat: Category
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    original: str | None = None


class ManualDetectionResponse(BaseModel):
    detection: Detection
    detections: list[Detection]


class DetectionPatchRequest(BaseModel):
    session_id: str
    cat: Category | None = None
    placeholder: str | None = None
    enabled: bool | None = None


@router.post("/manual")
async def add_manual(req: ManualDetectionRequest) -> ManualDetectionResponse:
    state = store.get(req.session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    if not state.doc_text:
        raise HTTPException(400, "No hay documento cargado")
    try:
        det = add_manual_detection(
            state, req.cat, req.start, req.end, req.original
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    store.save(state)
    return ManualDetectionResponse(detection=det, detections=state.detections)


@router.patch("/{detection_id}")
async def patch_detection(detection_id: int, req: DetectionPatchRequest) -> dict:
    state = store.get(req.session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    try:
        det = update_detection(
            state,
            detection_id,
            cat=req.cat,
            placeholder=req.placeholder,
            enabled=req.enabled,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    store.save(state)
    return {"detection": det, "detections": state.detections, "clusters": state.clusters}


@router.delete("/{detection_id}")
async def delete_detection(detection_id: int, session_id: str) -> dict:
    state = store.get(session_id)
    if not state:
        raise HTTPException(404, "Sesión no encontrada")
    try:
        remove_detection(state, detection_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    store.save(state)
    return {"detections": state.detections, "clusters": state.clusters}
