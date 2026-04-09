from __future__ import annotations

from pydantic import BaseModel, Field

from app.conversation.contracts.requests import ConversationRequest
from app.conversation.contracts.session_models import ConversationContext


class ExternalResearchResult(BaseModel):
    """
    Resultado placeholder para futuras consultas externas controladas.
    """

    enabled: bool = False
    findings: list[str] = Field(default_factory=list)


class ExternalResearchService:
    """
    Coordinador base para investigación externa futura.
    """

    def gather(
        self,
        request: ConversationRequest,
        context: ConversationContext,
    ) -> ExternalResearchResult:
        return ExternalResearchResult(enabled=False)
