from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://resale:resale@localhost:5435/resale_monitor_service"
    kafka_bootstrap_servers: str = "localhost:9092"
    # 정가 대비 이 배율을 넘으면 가격 이상치로 간주한다 (예: 1.3 = 정가의 130%)
    price_anomaly_ratio_threshold: float = 1.3
    habitual_score_threshold: float = 0.7

    class Config:
        env_file = ".env"


settings = Settings()
