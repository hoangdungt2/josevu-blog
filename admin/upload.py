"""Image upload: save pasted images to static/images."""
import re
import time
from pathlib import Path

from fastapi import UploadFile

from .config import settings

# content-type -> extension
CT_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}

MAX_BYTES = 20 * 1024 * 1024  # 20 MB


def _ext_from_filename(name: str) -> str:
    s = name.lower()
    for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"):
        if s.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ""


async def save_image(upload: UploadFile) -> tuple[str, Path]:
    ext = CT_EXT.get((upload.content_type or "").lower(), "") or _ext_from_filename(
        upload.filename or ""
    )
    if not ext:
        raise ValueError("Unsupported image type (use png, jpg, gif, webp, svg).")

    safe = re.sub(r"[^A-Za-z0-9._-]", "-", (upload.filename or "image").rsplit(".", 1)[0])
    safe = safe.strip("-") or "image"
    name = f"{int(time.time())}-{safe}{ext}"
    settings.images_dir.mkdir(parents=True, exist_ok=True)
    dest = settings.images_dir / name

    data = await upload.read()
    if len(data) > MAX_BYTES:
        raise ValueError("Image too large (max 20 MB).")
    dest.write_bytes(data)
    return f"/images/{name}", dest
