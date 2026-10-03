from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from core.container import ContainerError, build_container
from core.processor import MAX_UPLOAD_BYTES, safe_filename

router = APIRouter()


@router.post("/compress")
async def compress(files: list[UploadFile] = File(..., alias="files[]")):
    if not files:
        raise HTTPException(400, "Choose at least one file.")
    records = []
    total = 0
    try:
        for upload in files:
            try:
                name = safe_filename(upload.filename or "")
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
            data = await upload.read(MAX_UPLOAD_BYTES + 1)
            total += len(data)
            if total > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "Uploads are limited to 250 MB in total.")
            records.append((name, data))
        container = build_container(records)
    except ContainerError as exc:
        raise HTTPException(400, str(exc)) from exc
    finally:
        for upload in files:
            await upload.close()
    return StreamingResponse(iter([container]), media_type="application/vnd.skyso", headers={"Content-Disposition": 'attachment; filename="skyso_files.sky"', "Content-Length": str(len(container))})
