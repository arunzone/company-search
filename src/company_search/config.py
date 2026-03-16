from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_user: str = "admin"
    opensearch_password: str = "OpenSearch!C0mp@ny"
    opensearch_use_ssl: bool = True
    opensearch_verify_certs: bool = False
    opensearch_index: str = "companies"

    fastapi_host: str = "0.0.0.0"  # nosec B104
    fastapi_port: int = 8000
    log_level: str = "INFO"


settings = Settings()
