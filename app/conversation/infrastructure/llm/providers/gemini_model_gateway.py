from __future__ import annotations

import os

from google import genai

from app.core.config import settings
from app.conversation.infrastructure.llm.model_gateway import (
    ConversationModelGateway,
    ConversationModelInvocation,
    ConversationModelRawResponse,
)


class ConversationGeminiModelGateway(ConversationModelGateway):
    """
    Gateway Gemini aislado para el subsistema conversacional.
    """

    def __init__(self) -> None:
        use_vertexai = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower() in {
            "true",
            "1",
            "yes",
        }

        if use_vertexai:
            self._client = genai.Client()
        else:
            api_key = settings.agentic_models.api_key
            if not api_key:
                raise ValueError(
                    "AGENTIC_API_KEY está vacío. Configura la API key en el .env."
                )
            self._client = genai.Client(api_key=api_key)

    def invoke(
        self,
        invocation: ConversationModelInvocation,
    ) -> ConversationModelRawResponse:
        response = self._client.models.generate_content(
            model=invocation.model_name,
            contents=invocation.user_input,
            config={
                "system_instruction": invocation.system_instruction,
                "temperature": invocation.temperature,
                "response_mime_type": "application/json",
            },
        )

        return ConversationModelRawResponse(
            model_name=invocation.model_name,
            output_text=response.text or "",
            provider_name="gemini",
        )
