from __future__ import annotations

from openai import OpenAI

from app.core.config import settings
from app.conversation.infrastructure.llm.model_gateway import (
    ConversationModelGateway,
    ConversationModelInvocation,
    ConversationModelRawResponse,
)


class ConversationOpenAICompatibleModelGateway(ConversationModelGateway):
    """
    Gateway para backends compatibles con OpenAI Chat Completions.
    """

    def __init__(self) -> None:
        self._client = OpenAI(
            base_url=settings.agentic_models.api_base_url,
            api_key=settings.agentic_models.api_key,
        )

    def invoke(
        self,
        invocation: ConversationModelInvocation,
    ) -> ConversationModelRawResponse:
        response = self._client.chat.completions.create(
            model=invocation.model_name,
            temperature=invocation.temperature,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": invocation.system_instruction,
                },
                {
                    "role": "user",
                    "content": invocation.user_input,
                },
            ],
        )
        output_text = response.choices[0].message.content or ""

        return ConversationModelRawResponse(
            model_name=invocation.model_name,
            output_text=output_text,
            provider_name="openai_compatible",
        )
