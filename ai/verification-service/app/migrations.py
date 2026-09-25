from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import settings


def run_migrations() -> None:
    """Apply every pending schema migration before accepting traffic."""
    service_root = Path(__file__).resolve().parents[1]
    config = Config(str(service_root / "alembic.ini"))
    config.set_main_option("script_location", str(service_root / "migrations"))
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    command.upgrade(config, "head")
