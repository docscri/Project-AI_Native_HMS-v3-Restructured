import mimetypes
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from fastapi.responses import Response

from app.shared import files as storage
from app.shared.auth import require_any
from app.shared.db import get_db
from . import service

router = APIRouter(prefix="/api")


@router.post("/visits/{visit_id}/documents")
async def upload(visit_id: int, tasks: BackgroundTasks, file: UploadFile = File(...),
                 me=Depends(require_any("operations", "consultation", "patients")), db=Depends(get_db)):
    mime = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
    data = await file.read(storage.MAX_BYTES + 1)
    out, did = service.upload(db, me, visit_id, file.filename, mime, data)
    tasks.add_task(service.run_extraction, did)
    return out


@router.get("/visits/{visit_id}/documents")
def visit_documents(visit_id: int, me=Depends(require_any("operations", "consultation", "patients")), db=Depends(get_db)):
    return service.for_visit(db, me, visit_id)


@router.delete("/documents/{doc_id}")
def remove(doc_id: int, me=Depends(require_any("operations", "consultation", "patients")), db=Depends(get_db)):
    return service.remove(db, me, doc_id)


@router.post("/documents/{doc_id}/retry")
def retry(doc_id: int, tasks: BackgroundTasks, me=Depends(require_any("operations", "consultation", "patients")), db=Depends(get_db)):
    out = service.retry(db, me, doc_id)
    db.commit()   # the background read must see "processing"
    tasks.add_task(service.run_extraction, doc_id)
    return out


@router.get("/documents/{doc_id}/file")
def document_file(doc_id: int, me=Depends(require_any("consultation", "patients")), db=Depends(get_db)):
    data, d = service.file_of(db, me, doc_id)
    return Response(data, media_type=d["mime"], headers={"Content-Disposition": disposition(d["filename"])})


def disposition(filename: str) -> str:
    """Headers carry only plain ASCII: an ASCII stand-in for old browsers plus the real name UTF-8 encoded (RFC 6266)."""
    plain = "".join(c if c.isascii() and c.isprintable() and c not in '"\\' else "_" for c in filename) or "document"
    return f"inline; filename=\"{plain}\"; filename*=UTF-8''{quote(filename, safe='')}"
