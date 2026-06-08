from __future__ import annotations

from pathlib import PurePath

from fastapi import HTTPException, UploadFile, status
from pydantic import BaseModel

from reflexlearn.common.config import Settings, get_settings

_TEXT_EXTS = {"txt", "md", "html", "htm"}
_ZIP_EXTS = {"docx", "pptx"}
_VISIBILITY = {"public", "tenant", "private"}
_EXT_MIME = {
    "pdf": {"application/pdf"},
    "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    "pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    "html": {"text/html"},
    "htm": {"text/html"},
    "md": {"text/markdown", "text/plain"},
    "txt": {"text/plain"},
}


class ValidatedUpload(BaseModel):
    filename: str
    raw: bytes
    extension: str
    content_type: str


def validate_visibility(value: str) -> str:
    if value not in _VISIBILITY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_visibility",
        )
    return value


def _split_csv(value: str) -> set[str]:
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def _safe_filename(filename: str | None) -> str:
    name = PurePath((filename or "upload.bin").replace("\\", "/")).name
    return name or "upload.bin"


def _extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def _looks_like_text(raw: bytes) -> bool:
    if b"\x00" in raw[:4096]:
        return False
    try:
        raw[:4096].decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _validate_magic(ext: str, raw: bytes) -> None:
    if ext == "pdf" and not raw.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="file_content_mismatch",
        )
    if ext in _ZIP_EXTS and not raw.startswith(b"PK\x03\x04"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="file_content_mismatch",
        )
    if ext in _TEXT_EXTS and not _looks_like_text(raw):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="file_content_mismatch",
        )
    if ext == "md" and raw.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="file_content_mismatch",
        )


def _validate_mime_for_ext(ext: str, content_type: str) -> None:
    if not content_type:
        return
    if content_type not in _EXT_MIME.get(ext, set()):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="file_content_mismatch",
        )


async def read_validated_upload(
    file: UploadFile,
    settings: Settings | None = None,
) -> ValidatedUpload:
    cfg = settings or get_settings()
    filename = _safe_filename(file.filename)
    ext = _extension(filename)
    allowed_exts = _split_csv(cfg.allowed_upload_extensions)
    allowed_mimes = _split_csv(cfg.allowed_upload_mime_types)
    content_type = (file.content_type or "").split(";")[0].lower()

    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="unsupported_file_type",
        )
    if content_type and content_type not in allowed_mimes:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="unsupported_file_type",
        )
    _validate_mime_for_ext(ext, content_type)

    raw = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        raw.extend(chunk)
        if len(raw) > cfg.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="upload_too_large",
            )

    data = bytes(raw)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empty_upload",
        )
    _validate_magic(ext, data)
    return ValidatedUpload(
        filename=filename,
        raw=data,
        extension=ext,
        content_type=content_type,
    )
