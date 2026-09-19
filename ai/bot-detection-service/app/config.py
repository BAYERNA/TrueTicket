from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://botdetect:botdetect@localhost:5434/bot_detection_service"
    kafka_bootstrap_servers: str = "localhost:9092"
    acquisition_fraud_threshold: float = 0.7

    class Config:
        env_file = ".env"


settings = Settings()
