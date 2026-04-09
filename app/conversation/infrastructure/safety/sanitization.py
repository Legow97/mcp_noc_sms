from __future__ import annotations

from app.conversation.contracts.requests import ConversationRequest
from app.conversation.contracts.responses import ConversationAgentResult


class SanitizationService:
    """
    Placeholder para futura sanitización/redacción de datos sensibles.
    """

    def sanitize_request(self, request: ConversationRequest) -> ConversationRequest:
        return request

    def sanitize_response(
        self,
        response: ConversationAgentResult,
    ) -> ConversationAgentResult:
        return response
