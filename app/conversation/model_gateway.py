from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class ConversationModelInvocation(BaseModel):
    """
    Entrada estándar para invocar el cerebro LLM conversacional.
    """

    system_instruction: str = Field(..., min_length=1)
    user_input: str = Field(..., min_length=1)
    model_name: str = Field(..., min_length=1)
    temperature: float = 0.2


class ConversationModelRawResponse(BaseModel):
    """
    Respuesta textual cruda del proveedor LLM.
    """

    model_name: str = Field(..., min_length=1)
    output_text: str = Field(..., min_length=1)
    provider_name: str = Field(..., min_length=1)


class ConversationModelGateway(ABC):
    """
    Puerto LLM del subsistema conversacional.
    """

    @abstractmethod
    def invoke(
        self,
        invocation: ConversationModelInvocation,
    ) -> ConversationModelRawResponse:
        raise NotImplementedError
