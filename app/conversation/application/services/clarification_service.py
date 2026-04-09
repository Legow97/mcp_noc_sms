from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from app.conversation.contracts.requests import ConversationRequest
from app.conversation.contracts.session_models import ConversationContext


class ClarificationAssessment(BaseModel):
    """
    Evaluación liviana sobre si el turno requiere más datos.
    """

    needs_clarification: bool = False
    sufficiency_level: Literal[
        "sufficient_to_orient",
        "sufficient_for_history",
        "insufficient",
    ] = "sufficient_to_orient"
    is_troubleshooting: bool = False
    known_information: dict[str, str] = Field(default_factory=dict)
    missing_information: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)


class ClarificationService:
    """
    Evaluación liviana de suficiencia para guiar troubleshooting inicial.
    """

    _ERROR_PATTERNS = [
        "connection refused",
        "timeout",
        "error",
        "latencia",
        "caída",
        "caida",
        "no funciona",
        "no responde",
        "indisponible",
        "se está cargando",
        "se esta cargando",
        "network",
    ]
    _TECHNICAL_ENTITIES = {
        "apim": "APIM",
        "api": "API",
        "base de datos": "base de datos",
        "bd": "base de datos",
        "database": "base de datos",
        "backend": "backend",
        "servicio": "servicio",
    }

    def evaluate(
        self,
        request: ConversationRequest,
        context: ConversationContext,
    ) -> ClarificationAssessment:
        message = request.message.strip()
        normalized = message.lower()
        known_information = self._extract_known_information(normalized)
        is_troubleshooting = self._looks_like_troubleshooting(normalized)

        if context.history:
            known_information["has_session_context"] = "true"

        if context.historical_context.has_evidence:
            known_information["has_historical_evidence"] = "true"

        if is_troubleshooting:
            missing_information = self._missing_troubleshooting_information(
                known_information
            )
            sufficiency_level = self._resolve_sufficiency_level(
                known_information=known_information,
                has_history=context.historical_context.has_evidence,
                missing_information=missing_information,
            )

            return ClarificationAssessment(
                needs_clarification=bool(missing_information),
                sufficiency_level=sufficiency_level,
                is_troubleshooting=True,
                known_information=known_information,
                missing_information=missing_information,
                follow_up_questions=self._build_troubleshooting_questions(
                    missing_information
                ),
            )

        if len(message) >= 10:
            return ClarificationAssessment(
                known_information=known_information,
                sufficiency_level=(
                    "sufficient_for_history"
                    if context.historical_context.has_evidence
                    else "sufficient_to_orient"
                ),
            )

        return ClarificationAssessment(
            needs_clarification=True,
            sufficiency_level="insufficient",
            known_information=known_information,
            missing_information=["more_detail"],
            follow_up_questions=[
                (
                    "Puedes compartir más contexto del incidente, síntoma o "
                    "pregunta que quieres resolver?"
                )
            ],
        )

    def _extract_known_information(self, normalized_message: str) -> dict[str, str]:
        known: dict[str, str] = {}

        for token, entity in self._TECHNICAL_ENTITIES.items():
            if token in normalized_message:
                known["service_or_component"] = entity
                break

        if any(pattern in normalized_message for pattern in self._ERROR_PATTERNS):
            known["symptom"] = self._extract_symptom(normalized_message)

        if any(token in normalized_message for token in ["producción", "produccion", "prod"]):
            known["environment"] = "producción"
        elif any(token in normalized_message for token in ["qa", "certificación", "certificacion", "dev"]):
            known["environment"] = "no-producción"

        if any(token in normalized_message for token in ["una api", "solo una", "un servicio"]):
            known["scope"] = "uno"
        elif any(token in normalized_message for token in ["varias", "múltiples", "multiples", "todos"]):
            known["scope"] = "multiple"

        if re.search(r"\binc[0-9a-z-]*\d[0-9a-z-]*\b", normalized_message):
            known["incident_id"] = "presente"

        if any(token in normalized_message for token in ["reinici", "valid", "prob", "ya revis"]):
            known["validations_performed"] = "presente"

        if re.search(r"\b\d{1,2}:\d{2}\b", normalized_message) or any(
            token in normalized_message
            for token in ["hoy", "ayer", "desde", "hace ", "aprox"]
        ):
            known["approximate_time"] = "presente"

        return known

    def _looks_like_troubleshooting(self, normalized_message: str) -> bool:
        return any(pattern in normalized_message for pattern in self._ERROR_PATTERNS)

    @staticmethod
    def _missing_troubleshooting_information(
        known_information: dict[str, str],
    ) -> list[str]:
        required = [
            "service_or_component",
            "environment",
            "scope",
            "validations_performed",
            "approximate_time",
        ]
        labels = {
            "service_or_component": "servicio_o_componente_afectado",
            "environment": "entorno",
            "scope": "alcance",
            "validations_performed": "validaciones_realizadas",
            "approximate_time": "hora_aproximada",
        }
        return [
            labels[key]
            for key in required
            if key not in known_information
        ]

    @staticmethod
    def _resolve_sufficiency_level(
        *,
        known_information: dict[str, str],
        has_history: bool,
        missing_information: list[str],
    ) -> str:
        has_core_signal = any(
            key in known_information
            for key in ["service_or_component", "symptom", "incident_id"]
        )
        if not has_core_signal and len(missing_information) >= 4:
            return "insufficient"
        if has_history or has_core_signal:
            return "sufficient_for_history"
        return "sufficient_to_orient"

    @staticmethod
    def _build_troubleshooting_questions(
        missing_information: list[str],
    ) -> list[str]:
        if not missing_information:
            return []

        priority_questions = {
            "servicio_o_componente_afectado": "Qué sistema, API o componente exacto está afectado?",
            "entorno": "Ocurre en producción, QA u otro entorno?",
            "alcance": "Afecta una sola API/servicio o varios?",
            "validaciones_realizadas": "Qué validaciones o acciones ya realizaron?",
            "hora_aproximada": "Desde qué hora aproximada ocurre o cuándo se observó por primera vez?",
        }
        return [
            priority_questions[item]
            for item in missing_information[:3]
            if item in priority_questions
        ]

    @staticmethod
    def _extract_symptom(normalized_message: str) -> str:
        if "connection refused" in normalized_message:
            return "connection refused"
        if "timeout" in normalized_message:
            return "timeout"
        if "no funciona" in normalized_message:
            return "no funciona"
        if "network" in normalized_message:
            return "network"
        if "latencia" in normalized_message:
            return "latencia"
        if "error" in normalized_message:
            return "error"
        return "síntoma técnico"
