from pydantic import BaseSettings


class ApiClientSettings(BaseSettings):

    retry_attempts: int = 3

    retry_delay: int = 3

    service_host_legal: str = None

    service_host_storage: str = None

    class Config(object):
        env_file = ".env"
