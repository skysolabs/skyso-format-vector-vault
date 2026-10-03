from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from urllib.parse import quote

from core.container import ContainerError, inspect_container, restore_container
from core.processor import MAX_UPLOAD_BYTES, safe_filename

router = APIRouter()


async def read_sky(upload: UploadFile) -> bytes:
    if not upload.filename or not upload.filename.lower().endswith(".sky"):
        raise HTTPException(400, "Choose a .sky container.")
    data = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Skyso containers are limited to 250 MB.")
    return data


@router.post("/inspect")
async def inspect(sky: UploadFile = File(...)):
    data = await read_sky(sky)
    try:
        return inspect_container(data)
    except ContainerError as exc:
        raise HTTPException(400, str(exc)) from exc
    finally:
        await sky.close()


@router.post("/decompress")
async def decompress(sky: UploadFile = File(...), selected: str | None = Form(None)):
    data = await read_sky(sky)
    names = None
    if selected:
        try:
            import json
            names = json.loads(selected)
            if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
                raise ValueError
        except (ValueError, TypeError):
            raise HTTPException(400, "Invalid file selection.")
    try:
        payload, filename, media_type = restore_container(data, names)
    except ContainerError as exc:
        raise HTTPException(400, str(exc)) from exc
    finally:
        await sky.close()
    filename = safe_filename(filename)
    content_disposition = f"attachment; filename=download; filename*=UTF-8''{quote(filename, safe='')}"
    return Response(payload, media_type=media_type, headers={"Content-Disposition": content_disposition, "Content-Length": str(len(payload))})
