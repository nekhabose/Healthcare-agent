from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "CareGuard"
    app_version: str = "0.1.0"
    environment: str = "development"
    base_url: str = "https://api.careguard.health"
    domain: str = "api.careguard.health"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/careguard"

    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    s3_bucket: str = "careguard-discharge-docs"
    sns_escalation_topic_arn: str = ""

    # Anthropic
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    claude_max_tokens: int = 500

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # Epic FHIR
    epic_fhir_base_url: str = ""
    epic_client_id: str = ""
    epic_private_key_path: str = ""

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    # Celery / SQS
    celery_broker_url: str = "sqs://"
    celery_result_backend: str = "redis://localhost:6379/0"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
