import io
import logging

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
    """FR-011-1: 검표 시점 얼굴 캡처 이미지를 MinIO(S3 호환)에 저장하고 참조 경로를 반환한다."""
    client = get_client()
    client.put_object(
        settings.minio_bucket,
        object_name,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return f"{settings.minio_bucket}/{object_name}"
