from __future__ import annotations

from abc import ABC, abstractmethod

from app.conversation.application.reasoning.execution_context import (
    ConversationExecutionContext,
)


class ConversationSkill(ABC):
    """Contrato mínimo para skills intercambiables del flujo conversacional."""

    name: str

    @abstractmethod
    def is_enabled(self, context: ConversationExecutionContext) -> bool:
        raise NotImplementedError
