from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.conversation.clarification import ClarificationAssessment
from app.conversation.contracts.requests import ConversationRequest
from app.conversation.contracts.responses import (
    ConversationAgentResult,
    ConversationIntent,
    ConversationResponseStatus,
)
from app.conversation.contracts.session_models import (
    ConversationContext,
    ConversationSessionState,
)
from app.conversation.external_research import ExternalResearchResult
from app.conversation.model_gateway import (
    ConversationModelGateway,
    ConversationModelInvocation,
)
from app.conversation.model_gateway_factory import build_conversation_model_gateway
from app.conversation.prompt_loader import MarkdownPromptLoader


class ReasoningAgentLLMOutput(BaseModel):
    """
    Salida estructurada esperada del LLM conversacional.
    """

    intent: ConversationIntent = ConversationIntent.GENERAL
    status: ConversationResponseStatus = ConversationResponseStatus.COMPLETED
    response_text: str = Field(..., min_length=1)
    missing_information: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    active_incident_ids: list[str] = Field(default_factory=list)
    active_entities: list[str] = Field(default_factory=list)
    active_issue_summary: str | None = None
    latest_historical_matches: list[str] = Field(default_factory=list)
    troubleshooting_context: dict[str, Any] = Field(default_factory=dict)
    latest_guidance_summary: str | None = None


class ReasoningAgent:
    """
    Agente LLM responsable de interpretar el turno y producir una salida
    conversacional estructurada.
    """

    def __init__(
        self,
        model_gateway: ConversationModelGateway | None = None,
        prompt_loader: MarkdownPromptLoader | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> None:
        self._model_gateway = model_gateway or build_conversation_model_gateway()
        self._prompt_loader = prompt_loader or MarkdownPromptLoader(
            settings.conversation_reasoning.prompts_dir
        )
        self._model_name = model_name or settings.conversation_reasoning.model_name
        self._temperature = (
            temperature
            if temperature is not None
            else settings.conversation_reasoning.temperature
        )

    def respond(
        self,
        request: ConversationRequest,
        session_state: ConversationSessionState,
        context: ConversationContext,
        clarification: ClarificationAssessment,
        external_research: ExternalResearchResult,
    ) -> ConversationAgentResult:
        if not self._model_name:
            return self._fallback_response(
                request,
                session_state,
                clarification,
                context,
            )

        invocation = ConversationModelInvocation(
            system_instruction=self._prompt_loader.load_system_instruction(),
            user_input=self._build_user_input(
                request=request,
                session_state=session_state,
                context=context,
                clarification=clarification,
                external_research=external_research,
            ),
            model_name=self._model_name,
            temperature=self._temperature,
        )
        try:
            raw_response = self._model_gateway.invoke(invocation)
            llm_output = self._parse_llm_output(raw_response.output_text)
        except Exception as exc:
            print("[WARN] [REASONING AGENT] LLM invocation failed:", str(exc))
            return self._fallback_response(
                request,
                session_state,
                clarification,
                context,
            )

        return ConversationAgentResult(
            intent=llm_output.intent,
            response_text=llm_output.response_text,
            status=llm_output.status,
            missing_information=llm_output.missing_information,
            follow_up_questions=llm_output.follow_up_questions,
            active_incident_ids=llm_output.active_incident_ids,
            active_entities=llm_output.active_entities,
            active_issue_summary=llm_output.active_issue_summary,
            latest_historical_matches=llm_output.latest_historical_matches,
            troubleshooting_context=llm_output.troubleshooting_context,
            latest_guidance_summary=llm_output.latest_guidance_summary,
        )

    def _build_user_input(
        self,
        request: ConversationRequest,
        session_state: ConversationSessionState,
        context: ConversationContext,
        clarification: ClarificationAssessment,
        external_research: ExternalResearchResult,
    ) -> str:
        recent_history = [
            message.model_dump(mode="json")
            for message in session_state.history[-6:]
        ]
        payload: dict[str, Any] = {
            "user_message": request.message.strip(),
            "request_mode": request.mode.value,
            "metadata": request.metadata,
            "requested_capabilities": request.requested_capabilities,
            "session_state": {
                "session_id": session_state.session_id,
                "current_mode": session_state.current_mode.value,
                "awaiting_more_info": session_state.awaiting_more_info,
                "last_user_message": session_state.last_user_message,
                "last_agent_response": session_state.last_agent_response,
                "active_issue_summary": session_state.active_issue_summary,
                "active_incident_ids": session_state.active_incident_ids,
                "active_entities": session_state.active_entities,
                "pending_clarifications": session_state.pending_clarifications,
                "missing_information": session_state.missing_information,
                "latest_historical_matches": session_state.latest_historical_matches,
                "troubleshooting_context": session_state.troubleshooting_context,
                "latest_guidance_summary": session_state.latest_guidance_summary,
                "history_count": len(session_state.history),
                "recent_history": recent_history,
            },
            "context_summary": context.summary,
            "historical_context": context.historical_context.model_dump(mode="json"),
            "clarification_assessment": clarification.model_dump(mode="json"),
            "external_research": external_research.model_dump(mode="json"),
        }
        return json.dumps(payload, ensure_ascii=False)

    def _parse_llm_output(self, output_text: str) -> ReasoningAgentLLMOutput:
        payload_text = self._extract_json_object(output_text)
        try:
            payload = json.loads(payload_text)
            return ReasoningAgentLLMOutput.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(
                "El ReasoningAgent recibió una respuesta LLM no estructurada."
            ) from exc

    @staticmethod
    def _extract_json_object(output_text: str) -> str:
        stripped = output_text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
            stripped = re.sub(r"```$", "", stripped).strip()

        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end < start:
            return stripped

        return stripped[start : end + 1]

    def _fallback_response(
        self,
        request: ConversationRequest,
        session_state: ConversationSessionState,
        clarification: ClarificationAssessment,
        context: ConversationContext,
    ) -> ConversationAgentResult:
        message = request.message.strip()
        intent = self._infer_intent(message, clarification)
        if (
            intent == ConversationIntent.GENERAL
            and (
                session_state.active_issue_summary
                or session_state.awaiting_more_info
                or session_state.current_mode.value == "troubleshooting"
            )
        ):
            intent = ConversationIntent.TROUBLESHOOTING_REQUEST
        historical_context = context.historical_context

        if historical_context.semantic_matches:
            matches = [
                (
                    f"{match.case_id} (distancia={match.distance:.4f}): "
                    f"{self._compact_text(match.document_text, 180)}"
                )
                for match in historical_context.semantic_matches[:5]
            ]
            match_ids = [match.case_id for match in historical_context.semantic_matches[:5]]
            base_note = ""
            active_ids: list[str] = []
            if historical_context.primary_incident is not None:
                base_note = (
                    f" Tomé como base el incidente "
                    f"{historical_context.primary_incident.case_id}."
                )
                active_ids.append(historical_context.primary_incident.case_id)

            active_ids.extend(
                match.case_id for match in historical_context.semantic_matches[:5]
            )
            if intent == ConversationIntent.TROUBLESHOOTING_REQUEST:
                missing_information = self._remaining_missing_information(
                    clarification,
                    session_state,
                )
                follow_up_questions = self._prioritize_questions(
                    clarification.follow_up_questions
                    or session_state.pending_clarifications,
                    missing_information,
                )
                response_text = (
                    "El síntoma parece de troubleshooting y encontré evidencia histórica real "
                    "para orientar el siguiente paso."
                    f"{base_note} Coincidencias: "
                    + " | ".join(matches)
                    + ". Orientación inicial: valida conectividad desde APIM hacia el backend, "
                    "estado del backend y si el rechazo ocurre para una API o para varias. "
                    "No lo tomo como causa confirmada: el histórico solo aporta patrones similares."
                )
                if follow_up_questions:
                    response_text += " Para afinar el diagnóstico: " + " ".join(
                        follow_up_questions[:3]
                    )

                return ConversationAgentResult(
                    intent=ConversationIntent.TROUBLESHOOTING_REQUEST,
                    status=(
                        ConversationResponseStatus.NEEDS_CLARIFICATION
                        if missing_information
                        else ConversationResponseStatus.COMPLETED
                    ),
                    response_text=response_text,
                    missing_information=missing_information,
                    follow_up_questions=follow_up_questions,
                    active_incident_ids=list(dict.fromkeys(active_ids)),
                    active_entities=self._merge_entities(
                        session_state.active_entities,
                        self._extract_active_entities(message),
                    ),
                    active_issue_summary=self._build_issue_summary(
                        message,
                        session_state,
                    ),
                    latest_historical_matches=match_ids,
                    troubleshooting_context=clarification.known_information,
                    latest_guidance_summary=(
                        "Validar conectividad APIM-backend, estado del backend y alcance."
                    ),
                )

            return ConversationAgentResult(
                intent=ConversationIntent.HISTORICAL_RETRIEVAL_REQUEST,
                response_text=(
                    "Encontré evidencia histórica real en incidentes similares."
                    f"{base_note} Resultados: "
                    + " | ".join(matches)
                    + ". Usa estas referencias como contexto; no infiero una causa única si no aparece explícita en la evidencia."
                ),
                active_incident_ids=list(dict.fromkeys(active_ids)),
                latest_historical_matches=match_ids,
            )

        if historical_context.primary_incident is not None:
            incident = historical_context.primary_incident

            if historical_context.timeline_entries:
                timeline_lines = [
                    f"{entry.sequence_order}. {entry.event_time or 'sin hora'} - {entry.event_text}"
                    for entry in historical_context.timeline_entries[:8]
                ]
                return ConversationAgentResult(
                    intent=ConversationIntent.TIMELINE_REQUEST,
                    response_text=(
                        f"Recuperé el timeline real de {incident.case_id}: "
                        + " | ".join(timeline_lines)
                    ),
                    active_incident_ids=[incident.case_id],
                )

            raw_sms_note = (
                f" SMS/bitácora original: {incident.raw_sms}"
                if incident.raw_sms
                else " No encontré un SMS original persistido; uso los campos canónicos disponibles."
            )
            return ConversationAgentResult(
                intent=intent,
                response_text=(
                    f"Recuperé el incidente real {incident.case_id}. "
                    f"Estado: {incident.status}. "
                    f"Falla: {incident.failure_text or 'sin descripción de falla'}. "
                    f"Impacto: {incident.impact_text or 'sin impacto registrado'}."
                    f"{raw_sms_note}"
                ),
                active_incident_ids=[incident.case_id],
            )

        if (
            historical_context.semantic_query_source
            and not historical_context.semantic_matches
        ):
            missing_information = self._remaining_missing_information(
                clarification,
                session_state,
            )
            follow_up_questions = self._prioritize_questions(
                clarification.follow_up_questions
                or [
                    "Qué síntoma exacto, componente afectado e impacto observas?"
                ],
                missing_information,
            )
            return ConversationAgentResult(
                intent=(
                    ConversationIntent.TROUBLESHOOTING_REQUEST
                    if intent == ConversationIntent.TROUBLESHOOTING_REQUEST
                    else ConversationIntent.HISTORICAL_RETRIEVAL_REQUEST
                ),
                response_text=(
                    "Ejecuté búsqueda semántica histórica real, pero no encontré "
                    "resultados suficientemente útiles para fundamentar una respuesta. "
                    "Aun así puedo orientar el descarte inicial: confirma el componente "
                    "afectado, alcance, entorno y evidencia exacta del error antes de "
                    "asumir una causa."
                ),
                status=ConversationResponseStatus.NEEDS_CLARIFICATION,
                missing_information=missing_information,
                follow_up_questions=follow_up_questions,
                active_entities=self._merge_entities(
                    session_state.active_entities,
                    self._extract_active_entities(message),
                ),
                active_issue_summary=self._build_issue_summary(message, session_state),
                troubleshooting_context=clarification.known_information,
                latest_guidance_summary=(
                    "Sin matches históricos útiles; confirmar componente, entorno, alcance y error."
                ),
            )

        if intent == ConversationIntent.GREETING:
            return ConversationAgentResult(
                intent=intent,
                response_text=(
                    "Hola. Puedo ayudarte a preparar análisis de incidentes, "
                    "líneas de tiempo, consultas históricas o troubleshooting básico."
                ),
            )

        if intent == ConversationIntent.TIMELINE_REQUEST:
            incident_ids = self._extract_incident_ids(message)
            incident_note = f" para {', '.join(incident_ids)}" if incident_ids else ""
            return ConversationAgentResult(
                intent=intent,
                response_text=(
                    "Entendí que necesitas una línea de tiempo"
                    f"{incident_note}. En esta etapa aún no ejecuto retrieval histórico "
                    "real desde el flujo conversacional, pero la intención ya queda "
                    "clasificada para integrarlo luego."
                ),
                active_incident_ids=incident_ids,
            )

        if intent == ConversationIntent.TROUBLESHOOTING_REQUEST:
            missing_information = self._remaining_missing_information(
                clarification,
                session_state,
            )
            follow_up_questions = self._prioritize_questions(
                clarification.follow_up_questions
                or session_state.pending_clarifications
                or [
                    "Qué servicio exacto falla, desde cuándo ocurre y cuál es el impacto observado?"
                ],
                missing_information,
            )
            active_entities = self._merge_entities(
                session_state.active_entities,
                self._extract_active_entities(message),
            )
            issue_summary = self._build_issue_summary(message, session_state)
            return ConversationAgentResult(
                intent=intent,
                status=(
                    ConversationResponseStatus.NEEDS_CLARIFICATION
                    if missing_information
                    else ConversationResponseStatus.COMPLETED
                ),
                response_text=(
                    "Entendí el problema como troubleshooting operativo. "
                    "Orientación inicial: delimita alcance, entorno y componente; "
                    "si es `connection refused`, valida conectividad hacia el backend, "
                    "puerto/listener, estado del servicio destino y si el rechazo aparece "
                    "en logs de APIM o del backend. No confirmo causa todavía sin más evidencia."
                ),
                missing_information=missing_information,
                follow_up_questions=follow_up_questions,
                active_entities=active_entities,
                active_issue_summary=issue_summary,
                troubleshooting_context=clarification.known_information,
                latest_guidance_summary=(
                    "Delimitar alcance/entorno/componente y validar conectividad, listener y logs."
                ),
            )

        if clarification.needs_clarification:
            return ConversationAgentResult(
                intent=ConversationIntent.NEEDS_CLARIFICATION,
                response_text=(
                    "Necesito un poco más de contexto para ayudarte: qué incidente, "
                    "servicio o síntoma quieres revisar?"
                ),
                status=ConversationResponseStatus.NEEDS_CLARIFICATION,
                missing_information=clarification.missing_information,
                follow_up_questions=clarification.follow_up_questions,
                troubleshooting_context=clarification.known_information,
            )

        history_size = len(session_state.history)
        prior_message_note = ""
        if session_state.last_user_message:
            prior_message_note = (
                f" Último mensaje previo en sesión: '{session_state.last_user_message}'."
            )

        return ConversationAgentResult(
            intent=intent,
            response_text=(
                f"Entendí tu solicitud. Historial disponible: {history_size} mensajes."
                f"{prior_message_note}"
            ),
        )

    def _infer_intent(
        self,
        message: str,
        clarification: ClarificationAssessment,
    ) -> ConversationIntent:
        normalized = message.lower()

        if normalized in {"hola", "buenas", "hello", "hi"}:
            return ConversationIntent.GREETING

        if "línea de tiempo" in normalized or "linea de tiempo" in normalized:
            return ConversationIntent.TIMELINE_REQUEST

        if any(
            token in normalized
            for token in [
                "connection refused",
                "timeout",
                "error",
                "apim",
                "no funciona",
                "latencia",
                "network",
                "se está cargando",
                "se esta cargando",
            ]
        ):
            return ConversationIntent.TROUBLESHOOTING_REQUEST

        if any(token in normalized for token in ["histórico", "historico", "consulta", "buscar"]):
            return ConversationIntent.HISTORICAL_RETRIEVAL_REQUEST

        if clarification.needs_clarification:
            return ConversationIntent.NEEDS_CLARIFICATION

        return ConversationIntent.GENERAL

    @staticmethod
    def _extract_incident_ids(message: str) -> list[str]:
        return re.findall(r"\bINC(?=[0-9A-Z-]*\d)[0-9A-Z-]+\b", message.upper())

    @staticmethod
    def _compact_text(value: str, limit: int) -> str:
        normalized = " ".join(value.split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3] + "..."

    @staticmethod
    def _remaining_missing_information(
        clarification: ClarificationAssessment,
        session_state: ConversationSessionState,
    ) -> list[str]:
        missing = list(
            dict.fromkeys(
                [*clarification.missing_information, *session_state.missing_information]
            )
        )
        known_to_missing = {
            "service_or_component": "servicio_o_componente_afectado",
            "environment": "entorno",
            "scope": "alcance",
            "validations_performed": "validaciones_realizadas",
            "approximate_time": "hora_aproximada",
        }
        resolved = {
            missing_key
            for known_key, missing_key in known_to_missing.items()
            if known_key in clarification.known_information
        }
        return [item for item in missing if item not in resolved]

    @staticmethod
    def _prioritize_questions(
        questions: list[str],
        missing_information: list[str] | None = None,
    ) -> list[str]:
        filtered_questions = [
            question
            for question in questions
            if question
            and ReasoningAgent._question_still_relevant(
                question,
                missing_information or [],
            )
        ]
        return list(dict.fromkeys(filtered_questions))[:3]

    @staticmethod
    def _question_still_relevant(
        question: str,
        missing_information: list[str],
    ) -> bool:
        if not missing_information:
            return True

        normalized = question.lower()
        question_to_missing = {
            "producción": "entorno",
            "produccion": "entorno",
            "qa": "entorno",
            "una sola": "alcance",
            "varios": "alcance",
            "validaciones": "validaciones_realizadas",
            "acciones": "validaciones_realizadas",
            "desde": "hora_aproximada",
            "hora": "hora_aproximada",
            "sistema": "servicio_o_componente_afectado",
            "componente": "servicio_o_componente_afectado",
        }
        for token, missing_key in question_to_missing.items():
            if token in normalized:
                return missing_key in missing_information
        return True

    @staticmethod
    def _extract_active_entities(message: str) -> list[str]:
        normalized = message.lower()
        entities: list[str] = []
        if "apim" in normalized:
            entities.append("APIM")
        if "api" in normalized:
            entities.append("API")
        if any(token in normalized for token in ["base de datos", "bd", "database"]):
            entities.append("base de datos")
        if "backend" in normalized:
            entities.append("backend")
        return list(dict.fromkeys(entities))

    @staticmethod
    def _merge_entities(previous_entities: list[str], new_entities: list[str]) -> list[str]:
        return list(dict.fromkeys([*previous_entities, *new_entities]))

    @staticmethod
    def _build_issue_summary(
        message: str,
        session_state: ConversationSessionState,
    ) -> str:
        compact_message = ReasoningAgent._compact_text(message, 160)
        if session_state.active_issue_summary:
            return ReasoningAgent._compact_text(
                f"{session_state.active_issue_summary} | Nuevo dato: {compact_message}",
                260,
            )
        return compact_message
