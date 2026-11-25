"""Upload de documentos."""
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import MAX_UPLOAD_BYTES
from app.extraction import extract_docx
from app.extraction.pdf import extract_pdf_with_pages
from app.models.schemas import UploadResponse
from app.models.store import store

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "Nombre de archivo requerido")

    name_lower = file.filename.lower()
    if not name_lower.endswith((".docx", ".pdf")):
        raise HTTPException(400, "Formato no admitido. Usá .docx o .pdf")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(400, "Archivo vacío")
    if len(data) > MAX_UPLOAD_BYTES:
        limit_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise HTTPException(
            413,
            f"El archivo supera el límite de {limit_mb} MB. "
            "Dividilo o reducí su tamaño antes de cargarlo.",
        )

    pdf = None
    try:
        if name_lower.endswith(".docx"):
            text = extract_docx(data)
        elif name_lower.endswith(".pdf"):
            pdf = extract_pdf_with_pages(data)
            text = pdf.text
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"Error al leer archivo: {e}") from e

    session_id = store.create()
    state = store.get(session_id)
    assert state is not None

    state.doc_name = file.filename.rsplit(".", 1)[0]
    state.omitted_pdf_pages = pdf.omitted_pages if pdf else []
    state.doc_text = text
    state.doc_paragraphs = [p for p in text.split("\n\n") if p.strip()]
    store.save(state)

    return UploadResponse(
        session_id=session_id,
        doc_name=state.doc_name,
        char_count=len(text),
        pdf_page_count=pdf.page_count if pdf else None,
        omitted_pdf_pages=state.omitted_pdf_pages,
        paragraph_count=len(state.doc_paragraphs),
    )
