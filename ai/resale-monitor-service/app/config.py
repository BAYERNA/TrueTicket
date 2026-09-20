from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://resale:resale@localhost:5435/resale_monitor_service"
    kafka_bootstrap_servers: str = "localhost:9092"
    # 정가 대비 이 배율을 넘으면 가격 이상치로 간주한다 (예: 1.3 = 정가의 130%)
    price_anomaly_ratio_threshold: float = 1.3
    habitual_score_threshold: float = 0.7

    # FR-006: 크롤링 대상 리셀 플랫폼. MVP는 단일 소스만 지원하며, 여러 플랫폼을
    # 동시에 모니터링하려면 crawler.py의 SOURCES 목록을 확장한다.
    ticket_service_url: str = "http://localhost:8081"
    crawl_source_platform_name: str = "ticketbay"
    crawl_source_url: str = ""
    crawl_interval_minutes: int = 15
    jwt_secret: str = "change-me-in-production-at-least-32-bytes"
    jwt_issuer: str = "trueticket"
    internal_api_key: str = "change-me-in-production-internal-key"

    class Config:
        env_file = ".env"


settings = Settings()
