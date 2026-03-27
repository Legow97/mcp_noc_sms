from __future__ import annotations

from openai import OpenAI

from app.agentic.providers.model_gateway import BaseModelGateway
from app.agentic.providers.provider_models import (
    ModelInvocationContext,
    ModelRawResponse,
)
from app.core.config import settings


class OpenAICompatibleModelGateway(BaseModelGateway):
    """
    Gateway genérico para backends con API compatible con OpenAI.

    Este adaptador está pensado para el subsistema agentic y permite
    invocar distintos modelos configurables desde código o .env:
    - Qwen
    - Llama
    - DeepSeek
    - otros compatibles

    El orquestador no necesita saber nada del SDK concreto ni del backend.
    """

    def __init__(
        self,
        provider_name: str = "openai_compatible",
    ) -> None:
        self._provider_name = provider_name
        self._client = OpenAI(
            base_url=settings.agentic_models.api_base_url,
            api_key=settings.agentic_models.api_key,
        )

    def invoke(self, context: ModelInvocationContext) -> ModelRawResponse:
        """
        Ejecuta una invocación de chat completion compatible con OpenAI.
        """
        if not context.model_name:
            raise ValueError(
                "ModelInvocationContext.model_name es obligatorio para OpenAICompatibleModelGateway."
            )

        response = self._client.chat.completions.create(
            model=context.model_name,
            temperature=context.temperature if context.temperature is not None else 0.2,
            messages=[
                {
                    "role": "system",
                    "content": context.system_instruction,
                },
                {
                    "role": "user",
                    "content": context.user_input,
                },
            ],
        )

        output_text = response.choices[0].message.content or ""

        return ModelRawResponse(
            model_name=context.model_name,
            output_text=output_text,
            provider_name=self._provider_name,
        )