from __future__ import annotations

import os

from google import genai

from app.core.config import settings


class EmbeddingServiceError(RuntimeError):
    """Error base del subsistema de embeddings."""


class EmbeddingConfigurationError(EmbeddingServiceError):
    """La configuración del proveedor de embeddings es inválida."""


class EmbeddingProviderError(EmbeddingServiceError):
    """El proveedor de embeddings no pudo procesar la solicitud."""


class EmbeddingService:
    """
    Servicio de embeddings desacoplado del dominio y de la persistencia.
    """

    def __init__(
        self,
        *,
        provider_name: str | None = None,
        model_name: str | None = None,
        api_key: str | None = None,
        timeout_ms: int | None = None,
        use_vertexai: bool | None = None,
        client: object | None = None,
    ) -> None:
        self._provider_name = (
            provider_name or settings.retrieval.embedding_provider
        ).strip()
        self._model_name = (model_name or settings.retrieval.embedding_model).strip()
        self._api_key = (
            api_key
            if api_key is not None
            else settings.retrieval.gemini_api_key or settings.agentic_models.api_key
        ).strip()
        self._timeout_ms = (
            timeout_ms
            if timeout_ms is not None
            else settings.retrieval.timeout_ms
        )
        self._use_vertexai = (
            use_vertexai
            if use_vertexai is not None
            else self._resolve_use_vertexai()
        )
        self._client = client

        if not self._provider_name:
            raise EmbeddingConfigurationError(
                "RETRIEVAL_EMBEDDING_PROVIDER no puede estar vacío."
            )
        if self._provider_name.lower() != "gemini":
            raise EmbeddingConfigurationError(
                f"Proveedor de embeddings no soportado: {self._provider_name!r}."
            )
        if not self._model_name:
            raise EmbeddingConfigurationError(
                "RETRIEVAL_EMBEDDING_MODEL no puede estar vacío."
            )
        if self._timeout_ms <= 0:
            raise EmbeddingConfigurationError(
                "RETRIEVAL_EMBEDDING_TIMEOUT_MS debe ser mayor que cero."
            )

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_text(
        self,
        document_text: str,
        *,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> list[float]:
        normalized_text = document_text.strip()
        if not normalized_text:
            raise ValueError("document_text no puede estar vacío.")
        normalized_task_type = task_type.strip().upper()
        if not normalized_task_type:
            raise ValueError("task_type no puede estar vacío.")

        try:
            response = self._get_client().models.embed_content(
                model=self._model_name,
                contents=normalized_text,
                config={
                    "task_type": normalized_task_type,
                },
            )
        except EmbeddingConfigurationError:
            raise
        except Exception as exc:
            raise EmbeddingProviderError(
                f"No se pudo generar embedding con {self._provider_name}: {exc}"
            ) from exc

        embeddings = getattr(response, "embeddings", None)
        if not embeddings:
            raise EmbeddingProviderError(
                "El proveedor devolvió una respuesta sin embeddings."
            )

        values = getattr(embeddings[0], "values", None)
        if not values:
            raise EmbeddingProviderError(
                "El proveedor devolvió un embedding vacío."
            )

        return [float(value) for value in values]

    def _get_client(self) -> genai.Client:
        if self._client is not None:
            return self._client  # type: ignore[return-value]

        http_options = {"timeout": self._timeout_ms}

        if self._use_vertexai:
            self._client = genai.Client(http_options=http_options)
            return self._client

        if not self._api_key:
            raise EmbeddingConfigurationError(
                "RETRIEVAL_GEMINI_API_KEY/AGENTIC_API_KEY está vacío para Gemini Developer API."
            )

        self._client = genai.Client(
            api_key=self._api_key,
            http_options=http_options,
        )
        return self._client

    def _resolve_use_vertexai(self) -> bool:
        if settings.retrieval.use_vertexai is not None:
            return settings.retrieval.use_vertexai

        return os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower() in {
            "true",
            "1",
            "yes",
        }
