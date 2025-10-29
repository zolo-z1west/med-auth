# backend/app/routes/capture.py
import re
import time
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from app.utils import save_upload_file

router = APIRouter()
UPLOAD_DIR = Path("/tmp/med_auth_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _safe_filename(name: str) -> str:
    name = Path(name).name
    return re.sub(r'[^A-Za-z0-9_.-]', '_', name)

@router.post("/capture")
async def capture(request: Request, image: UploadFile = File(...), source: str = Form(...)):
    try:
        if not image or not getattr(image, "content_type", None):
            raise HTTPException(status_code=400, detail="no file uploaded")

        if not image.content_type.startswith("image"):
            raise HTTPException(status_code=400, detail="uploaded file is not an image")

        safe = _safe_filename(image.filename or "upload")
        ts = int(time.time() * 1000)
        dest_name = f"{ts}_{safe}"
        dest = UPLOAD_DIR / dest_name

        await save_upload_file(image, dest)

        size = dest.stat().st_size if dest.exists() else 0
        logger.info("Saved upload %s from %s (%d bytes)", dest_name, source, size)
        return JSONResponse({"filename": dest_name, "size": size, "source": source})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("unexpected error in /capture")
        # return minimal internal error detail to client
        raise HTTPException(status_code=500, detail="internal server error")
