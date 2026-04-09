from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.conversation.application.reasoning.reasoning_agent import ReasoningAgent
from app.conversation.application.services.clarification_service import (
    ClarificationService,
)
from app.conversation.application.services.context_builder import ContextBuilder
from app.conversation.contracts.requests import ConversationRequest
from app.conversation.contracts.responses import ConversationResponse
from app.conversation.contracts.session_models import (
    ConversationMessage,
    ConversationSessionState,
)
from app.conversation.infrastructure.safety.sanitization import SanitizationService
from app.conversation.infrastructure.session.session_store import (
    InMemorySessionStore,
    SessionStore,
)


class ConversationOrchestrator:
    """
    Coordina el flujo conversacional sin absorber lógica cognitiva
    ni detalles de infraestructura concreta.
    """

    def __init__(
        self,
        reasoning_agent: ReasoningAgent | None = None,
        context_builder: ContextBuilder | None = None,
        clarification_service: ClarificationService | None = None,
        session_store: SessionStore | None = None,
        sanitization_service: SanitizationService | None = None,
    ) -> None:
        self._reasoning_agent = reasoning_agent or ReasoningAgent()
        self._context_builder = context_builder or ContextBuilder()
        self._clarification_service = clarification_service or ClarificationService()
        self._session_store = session_store or InMemorySessionStore()
        self._sanitization_service = sanitization_service or SanitizationService()

    def handle(self, request: ConversationRequest) -> ConversationResponse:
        sanitized_request = self._sanitization_service.sanitize_request(request)
        session_id = sanitized_request.session_id or self._build_session_id()
        session_state = self._session_store.get_session(
            session_id=session_id,
            mode=sanitized_request.mode,
        )
        context = self._context_builder.build(
            request=sanitized_request,
            session_state=session_state,
        )
        clarification = self._clarification_service.evaluate(
            request=sanitized_request,
            context=context,
        )
        agent_result = self._reasoning_agent.respond(
            request=sanitized_request,
            session_state=session_state,
            context=context,
            clarification=clarification,
        )
        sanitized_response = self._sanitization_service.sanitize_response(agent_result)
        updated_session_state = self._build_updated_session_state(
            session_state=session_state,
            request=sanitized_request,
            intent=sanitized_response.intent.value,
            response_text=sanitized_response.response_text,
            needs_clarification=bool(sanitized_response.missing_information),
            missing_information=sanitized_response.missing_information,
            follow_up_questions=sanitized_response.follow_up_questions,
            active_incident_ids=sanitized_response.active_incident_ids,
            active_entities=sanitized_response.active_entities,
            active_issue_summary=sanitized_response.active_issue_summary,
            latest_historical_matches=sanitized_response.latest_historical_matches,
            troubleshooting_context=sanitized_response.troubleshooting_context,
            latest_guidance_summary=sanitized_response.latest_guidance_summary,
        )
        self._session_store.save_session(updated_session_state)

        return ConversationResponse(
            session_id=session_id,
            mode=sanitized_request.mode,
            status=sanitized_response.status,
            response_text=sanitized_response.response_text,
            context_summary=context.summary,
            missing_information=sanitized_response.missing_information,
            follow_up_questions=sanitized_response.follow_up_questions,
            active_issue_summary=sanitized_response.active_issue_summary,
        )

    @staticmethod
    def _build_session_id() -> str:
        return f"conv-{uuid4().hex}"

    @staticmethod
    def _build_updated_session_state(
        session_state: ConversationSessionState,
        request: ConversationRequest,
        intent: str,
        response_text: str,
        needs_clarification: bool,
        missing_information: list[str],
        follow_up_questions: list[str],
        active_incident_ids: list[str],
        active_entities: list[str],
        active_issue_summary: str | None,
        latest_historical_matches: list[str],
        troubleshooting_context: dict[str, Any],
        latest_guidance_summary: str | None,
    ) -> ConversationSessionState:
        updated_state = session_state.model_copy(deep=True)
        updated_state.current_mode = request.mode
        updated_state.awaiting_more_info = needs_clarification
        updated_state.last_user_message = request.message.strip()
        updated_state.last_agent_response = response_text
        updated_state.pending_clarifications = list(follow_up_questions)
        updated_state.missing_information = list(missing_information)
        if active_issue_summary:
            updated_state.active_issue_summary = active_issue_summary
        if latest_historical_matches:
            updated_state.latest_historical_matches = list(latest_historical_matches)
        if troubleshooting_context:
            updated_state.troubleshooting_context = {
                **updated_state.troubleshooting_context,
                **troubleshooting_context,
            }
        if latest_guidance_summary:
            updated_state.latest_guidance_summary = latest_guidance_summary
        updated_state.active_incident_ids = list(
            dict.fromkeys([*updated_state.active_incident_ids, *active_incident_ids])
        )
        updated_state.active_entities = list(
            dict.fromkeys([*updated_state.active_entities, *active_entities])
        )
        updated_state.attributes["last_detected_intent"] = intent
        updated_state.history.extend(
            [
                ConversationMessage(
                    role="user",
                    content=request.message.strip(),
                ),
                ConversationMessage(
                    role="assistant",
                    content=response_text,
                ),
            ]
        )
        return updated_state
