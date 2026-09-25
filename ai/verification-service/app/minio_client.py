import io
import logging
import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from minio import Minio

from app.config import settings

logger = logging.getLogger(__name__)

_client: Minio | None = None


def get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        if not _client.bucket_exists(settings.minio_bucket):
            _client.make_bucket(settings.minio_bucket)
    return _client


def upload_snapshot(object_name: str, data: bytes, content_type: str = "image/jpeg") -> str:
    """얼굴 캡처를 AES-256-GCM으로 암호화한 뒤 오브젝트 스토리지에 저장한다."""
    key = base64.urlsafe_b64decode(settings.snapshot_encryption_key)
    if len(key) != 32:
        raise RuntimeError("SNAPSHOT_ENCRYPTION_KEY must decode to exactly 32 bytes")
    nonce = os.urandom(12)
    encrypted = nonce + AESGCM(key).encrypt(nonce, data, object_name.encode("utf-8"))
    client = get_client()
    client.put_object(
        settings.minio_bucket,
        object_name,
        io.BytesIO(encrypted),
        length=len(encrypted),
        content_type="application/octet-stream",
    )
    return f"{settings.minio_bucket}/{object_name}"


def delete_snapshot(snapshot_uri: str) -> None:
    prefix = f"{settings.minio_bucket}/"
    if not snapshot_uri.startswith(prefix):
        raise ValueError("Invalid snapshot URI")
    get_client().remove_object(settings.minio_bucket, snapshot_uri[len(prefix):])
