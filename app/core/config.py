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
    """Configuración general de proveedores de modelos del sistema."""

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


class AgenticModelSettings(BaseAppSettings):
    """Configuración del subsistema agentic de extracción canónica."""

    primary_extractor_model: str = Field(
        default="Qwen/Qwen2.5-7B-Instruct",
        alias="PRIMARY_EXTRACTOR_MODEL",
    )
    semantic_judge_model: str = Field(
        default="meta-llama/Llama-3.1-8B-Instruct",
        alias="SEMANTIC_JUDGE_MODEL",
    )
    fallback_extractor_model: str = Field(
        default="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        alias="FALLBACK_EXTRACTOR_MODEL",
    )
    provider: str = Field(
        default="openai_compatible",
        alias="AGENTIC_PROVIDER",
    )
    api_base_url: str = Field(
        default="",
        alias="AGENTIC_API_BASE_URL",
    )
    api_key: str = Field(
        default="",
        alias="AGENTIC_API_KEY",
    )


class RetrievalSettings(BaseAppSettings):
    """Configuración del subsistema de retrieval semántico."""

    embedding_provider: str = Field(
        default="gemini",
        alias="RETRIEVAL_EMBEDDING_PROVIDER",
    )
    embedding_model: str = Field(
        default="gemini-embedding-001",
        alias="RETRIEVAL_EMBEDDING_MODEL",
    )
    document_version: str = Field(
        default="v1",
        alias="RETRIEVAL_DOCUMENT_VERSION",
    )
    gemini_api_key: str = Field(
        default="",
        alias="RETRIEVAL_GEMINI_API_KEY",
    )
    timeout_ms: int = Field(
        default=30000,
        alias="RETRIEVAL_EMBEDDING_TIMEOUT_MS",
    )
    use_vertexai: bool | None = Field(
        default=None,
        alias="RETRIEVAL_USE_VERTEXAI",
    )


class ConversationRedisSettings(BaseAppSettings):
    """Configuración de memoria corta conversacional sobre Redis."""

    enabled: bool = Field(
        default=True,
        alias="CONVERSATION_REDIS_ENABLED",
    )
    host: str = Field(
        default="localhost",
        alias="CONVERSATION_REDIS_HOST",
    )
    port: int = Field(
        default=6379,
        alias="CONVERSATION_REDIS_PORT",
    )
    db: int = Field(
        default=0,
        alias="CONVERSATION_REDIS_DB",
    )
    password: str = Field(
        default="",
        alias="CONVERSATION_REDIS_PASSWORD",
    )
    session_ttl_seconds: int = Field(
        default=3600,
        alias="CONVERSATION_SESSION_TTL_SECONDS",
    )
    key_prefix: str = Field(
        default="conversation:session",
        alias="CONVERSATION_REDIS_KEY_PREFIX",
    )


class ConversationReasoningSettings(BaseAppSettings):
    """Configuración del cerebro LLM del agente conversacional."""

    provider: str = Field(
        default="gemini",
        alias="BRAIN_REASONING_PROVIDER",
    )
    model_name: str = Field(
        default="",
        alias="BRAIN_REASONING_AGENT",
    )
    temperature: float = Field(
        default=0.2,
        alias="BRAIN_REASONING_TEMPERATURE",
    )
    prompts_dir: str = Field(
        default="app/conversation/prompts",
        alias="BRAIN_REASONING_PROMPTS_DIR",
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
        self.agentic_models = AgenticModelSettings()
        self.retrieval = RetrievalSettings()
        self.conversation_redis = ConversationRedisSettings()
        self.conversation_reasoning = ConversationReasoningSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Devuelve una única instancia cacheada de configuración.

    Esto evita recrear settings múltiples veces y centraliza el acceso
    a la configuración del servicio.
    """
    return Settings()


settings = get_settings()
