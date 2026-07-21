from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DATA_DIR = Path.home() / ".pokerpete"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POKERPETE_")

    database_path: Path = DATA_DIR / "pokerpete.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"


settings = Settings()
