"""Esquemas Pydantic."""
from typing import Literal

from pydantic import BaseModel, Field

Category = Literal[
    "PERSONA",
    "DNI",
    "CUIT",
    "EMPRESA",
    "EMAIL",
    "TELEFONO",
    "DOMICILIO",
    "EXPEDIENTE",
    "ORGANISMO",
    "PATENTE",
    "OTRO",
]
LabelMode = Literal["cat", "gen", "ini"]
ClusterStatus = Literal["suggested", "confirmed", "rejected"]
Confidence = Literal["alta", "media", "baja"]


class Position(BaseModel):
    start: int
    end: int
    raw: str = ""


class Mention(BaseModel):
    id: str
    cat: Category
    surface: str
    start: int
    end: int
    norm: str = ""
    source_layer: str = "regex"


class Detection(BaseModel):
    id: int
    cat: Category
    original: str
    placeholder: str
    enabled: bool = True
    positions: list[Position] = Field(default_factory=list)
    mention_ids: list[str] = Field(default_factory=list)
    cluster_id: str | None = None
    manual_placeholder: bool = False
    user_added: bool = False


class ClusterAddDetectionsRequest(BaseModel):
    detection_ids: list[int]


class ClusterCreateRequest(BaseModel):
    detection_ids: list[int]
    cat: Category | None = None


class Cluster(BaseModel):
    cluster_id: str
    cat: Category
    canonical_label: str | None = None
    placeholder: str | None = None
    mention_ids: list[str] = Field(default_factory=list)
    surfaces: list[str] = Field(default_factory=list)
    confidence: Confidence = "media"
    status: ClusterStatus = "suggested"
    reasons: list[str] = Field(default_factory=list)


class SessionState(BaseModel):
    session_id: str
    doc_name: str = "documento"
    doc_text: str = ""
    doc_paragraphs: list[str] = Field(default_factory=list)
    mentions: list[Mention] = Field(default_factory=list)
    detections: list[Detection] = Field(default_factory=list)
    clusters: list[Cluster] = Field(default_factory=list)
    label_mode: LabelMode = "cat"
    enabled_categories: list[Category] = Field(default_factory=list)


class UploadResponse(BaseModel):
    session_id: str
    doc_name: str
    char_count: int
    paragraph_count: int
    message: str = "Documento cargado correctamente"


class AnalyzeRequest(BaseModel):
    session_id: str
    label_mode: LabelMode = "cat"
    enabled_categories: list[Category] | None = None


class CancelRequest(BaseModel):
    session_id: str


class AnalyzeResponse(BaseModel):
    session_id: str
    detections: list[Detection]
    clusters: list[Cluster]
    stats: dict[str, int]


class ClusterUpdateRequest(BaseModel):
    placeholder: str | None = None
    canonical_label: str | None = None


class ClusterSplitRequest(BaseModel):
    mention_ids: list[str]


class ClusterRemoveSurfaceRequest(BaseModel):
    surface: str


class ClusterMergeRequest(BaseModel):
    cluster_ids: list[str]


class ClusterAbsorbRequest(BaseModel):
    source_cluster_id: str


class ExportFormatOptions(BaseModel):
    font_name: str = "Times New Roman"
    font_size_pt: int = Field(default=12, ge=8, le=24)
    line_spacing: float = Field(default=1.5, ge=1.0, le=3.0)
    margin_cm: float = Field(default=3.0, ge=1.0, le=5.0)
    margin_top_bottom_cm: float = Field(default=2.5, ge=1.0, le=5.0)
    alignment: Literal["left", "justify", "center", "right"] = "justify"


class ExportRequest(BaseModel):
    session_id: str
    use_confirmed_only: bool = False


class ExportDocumentRequest(BaseModel):
    """Exportación con texto editado y formato opcional."""

    session_id: str
    use_confirmed_only: bool = False
    text: str | None = None
    format: ExportFormatOptions | None = None


class AnonymizedPreviewResponse(BaseModel):
    session_id: str
    doc_name: str
    text: str


class ConfirmResponse(BaseModel):
    cluster: Cluster
    detections: list[Detection]


class SearchAndAnonymizeRequest(BaseModel):
    """Anonimización a partir del buscador del preview.

    El frontend ya calculó `positions` (matching client-side sobre `doc_text`,
    típicamente insensible a mayúsculas y a acentos). El backend solo valida,
    deduplica y crea/extiende la detección.
    """

    session_id: str
    cat: Category
    original: str
    positions: list[Position]
    placeholder: str | None = None
