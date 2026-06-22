"""Upload de documentos."""
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.extraction import extract_docx, extract_pdf
from app.models.schemas import UploadResponse
from app.models.store import store

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "Nombre de archivo requerido")

    name_lower = file.filename.lower()
    data = await file.read()
    if not data:
        raise HTTPException(400, "Archivo vacío")

    try:
        if name_lower.endswith(".docx"):
            text = extract_docx(data)
        elif name_lower.endswith(".pdf"):
            text = extract_pdf(data)
        else:
            raise HTTPException(400, "Formato no admitido. Usa .docx o .pdf")
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"Error al leer archivo: {e}") from e

    session_id = store.create()
    state = store.get(session_id)
    assert state is not None

    state.doc_name = file.filename.rsplit(".", 1)[0]
    state.doc_text = text
    state.doc_paragraphs = [p for p in text.split("\n\n") if p.strip()]
    store.save(state)

    return UploadResponse(
        session_id=session_id,
        doc_name=state.doc_name,
        char_count=len(text),
        paragraph_count=len(state.doc_paragraphs),
    )
