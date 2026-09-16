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

    class Config:
        env_file = ".env"


settings = Settings()
