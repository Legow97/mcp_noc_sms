from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """Base común para todos los bloques de configuración."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class AppSettings(BaseAppSettings):
    """Configuración general de la aplicación."""

    name: str = Field(
        default="Incident Operational Memory Service",
        alias="APP_NAME",
    )
    environment: str = Field(
        default="development",
        alias="APP_ENV",
    )
    debug: bool = Field(
        default=True,
        alias="APP_DEBUG",
    )
    host: str = Field(
        default="127.0.0.1",
        alias="APP_HOST",
    )
    port: int = Field(
        default=8000,
        alias="APP_PORT",
    )


class DatabaseSettings(BaseAppSettings):
    """Configuración de conexión a base de datos."""

    url: str = Field(
        ...,
        alias="DATABASE_URL",
    )


class ModelProviderSettings(BaseAppSettings):
    """Configuración de proveedores de modelos."""

    default_provider: str = Field(
        default="gemini",
        alias="DEFAULT_MODEL_PROVIDER",
    )
    fallback_provider: str = Field(
        default="qwen",
        alias="FALLBACK_MODEL_PROVIDER",
    )
    gemini_api_key: str = Field(
        default="",
        alias="GEMINI_API_KEY",
    )
    qwen_base_url: str = Field(
        default="http://localhost:11434",
        alias="QWEN_BASE_URL",
    )


class LoggingSettings(BaseAppSettings):
    """Configuración de logging."""

    level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )


class FeatureSettings(BaseAppSettings):
    """Feature flags y switches operativos."""

    allow_external_sources: bool = Field(
        default=False,
        alias="ALLOW_EXTERNAL_SOURCES",
    )


class Settings:
    """
    Objeto raíz de configuración.

    Agrupa bloques especializados para mantener separación de responsabilidades
    y permitir evolución del sistema sin convertir config.py en una clase
    monolítica difícil de mantener.
    """

    def __init__(self) -> None:
        self.app = AppSettings()
        self.database = DatabaseSettings()
        self.models = ModelProviderSettings()
        self.logging = LoggingSettings()
        self.features = FeatureSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Devuelve una única instancia cacheada de configuración.

    Esto evita recrear settings múltiples veces y centraliza el acceso
    a la configuración del servicio.
    """
    return Settings()


settings = get_settings()