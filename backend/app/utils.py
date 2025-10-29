# backend/app/utils.py
import aiofiles
from fastapi import UploadFile, HTTPException
from pathlib import Path

MAX_BYTES = 10 * 1024 * 1024  # 10 MB

async def save_upload_file(upload_file: UploadFile, destination: Path) -> None:
    """
    Save UploadFile to destination safely.
    Enforces a MAX_BYTES limit and writes in chunks to avoid OOM.
    Raises HTTPException(413) on too-large uploads.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    # ensure file pointer at start
    try:
        await upload_file.seek(0)
    except Exception:
        # some UploadFile implementations do not support seek; ignore
        pass

    total = 0
    try:
        async with aiofiles.open(destination, "wb") as out_file:
            while True:
                chunk = await upload_file.read(1024 * 64)  # 64KB
                if not chunk:
                    break
                if isinstance(chunk, str):
                    # unexpected text; raise
                    raise HTTPException(status_code=400, detail="uploaded file returned text instead of bytes")
                total += len(chunk)
                if total > MAX_BYTES:
                    # cleanup partial file
                    await out_file.close()
                    try:
                        destination.unlink(missing_ok=True)
                    except Exception:
                        pass
                    raise HTTPException(status_code=413, detail="file too large")
                await out_file.write(chunk)
    finally:
        # attempt to close underlying file if present
        try:
            await upload_file.close()
        except Exception:
            pass
