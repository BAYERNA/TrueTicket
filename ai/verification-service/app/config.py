from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://verify:verify@localhost:5436/verification_service"
    ticket_service_url: str = "http://localhost:8081"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "trueticket"
    minio_secret_key: str = "trueticket123"
    minio_secure: bool = False
    minio_bucket: str = "verification-snapshots"

    face_match_threshold: float = 0.75
    yolo_face_model_path: str = "yolov8n-face.pt"
    jwt_secret: str = "change-me-in-production-at-least-32-bytes"
    jwt_issuer: str = "trueticket"
    internal_api_key: str = "change-me-in-production-internal-key"
    otel_exporter_otlp_endpoint: str = "http://localhost:4318/v1/traces"
    snapshot_encryption_key: str = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    snapshot_retention_days: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
