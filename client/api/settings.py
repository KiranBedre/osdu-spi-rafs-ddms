from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiClientSettings(BaseSettings):

    model_config = SettingsConfigDict(env_file=".env")

    retry_attempts: int = 3

    retry_delay: int = 3

    verify_ssl: bool = True

    service_host_legal: Optional[str] = None

    service_host_storage: Optional[str] = None
