from __future__ import annotations

import os

from google import genai

from app.agentic.providers.model_gateway import BaseModelGateway
from app.agentic.providers.provider_models import (
    ModelInvocationContext,
    ModelRawResponse,
)
from app.core.config import settings


class GeminiModelGateway(BaseModelGateway):
    """
    Gateway real para Gemini usando el SDK oficial google-genai.

    Esta versión soporta configuración extra opcional para structured outputs.
    """

    def __init__(
        self,
        provider_name: str = "gemini",
    ) -> None:
        use_vertexai = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower() in {
            "true",
            "1",
            "yes",
        }

        self._provider_name = provider_name
        if use_vertexai:
            self._client = genai.Client()
        else:
            if not settings.agentic_models.api_key:
                raise ValueError(
                    "AGENTIC_API_KEY está vacío. Configura la API key en el .env."
                )

            self._client = genai.Client(api_key=settings.agentic_models.api_key)

    def invoke(self, context: ModelInvocationContext) -> ModelRawResponse:
        """
        Ejecuta una invocación simple de texto contra Gemini.
        """
        if not context.model_name:
            raise ValueError(
                "ModelInvocationContext.model_name es obligatorio para GeminiModelGateway."
            )

        config: dict = {
            "system_instruction": context.system_instruction,
            "temperature": context.temperature
            if context.temperature is not None
            else 0.2,
        }

        # Permite pasar structured output u otras opciones desde el contexto
        extra_config = getattr(context, "extra_config", None)
        if isinstance(extra_config, dict):
            config.update(extra_config)

        response = self._client.models.generate_content(
            model=context.model_name,
            contents=context.user_input,
            config=config,
        )

        return ModelRawResponse(
            model_name=context.model_name,
            output_text=response.text or "",
            provider_name=self._provider_name,
        )
