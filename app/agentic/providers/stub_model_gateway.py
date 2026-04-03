from __future__ import annotations

from app.agentic.providers.model_gateway import BaseModelGateway
from app.agentic.providers.provider_models import (
    ModelInvocationContext,
    ModelRawResponse,
)


class StubModelGateway(BaseModelGateway):
    """
    Implementación stub del gateway de modelos.

    Permite simular distintos escenarios del subsistema agentic:
    - extractor principal aceptado
    - juez rechaza
    - fallback activado
    - juez final acepta o rechaza

    El comportamiento se controla desde `scenario`.

    Esta clase está pensada para:
    - probar el orquestador sin modelos reales
    - iterar fácilmente escenarios
    - documentar el comportamiento esperado del flujo agentic
    """

    def __init__(
        self,
        provider_name: str = "stub_provider",
        default_model_name: str = "stub-model-v1",
        scenario: str = "happy_path",
    ) -> None:
        self._provider_name = provider_name
        self._default_model_name = default_model_name
        self._scenario = scenario

    def invoke(self, context: ModelInvocationContext) -> ModelRawResponse:
        """
        Devuelve una salida simulada según:
        - task_name
        - scenario

        Esto emula el comportamiento de un proveedor/modelo real.
        """
        output_text = self._build_stub_output(context)

        return ModelRawResponse(
            model_name=context.model_name or self._default_model_name,
            output_text=output_text,
            provider_name=self._provider_name,
        )

    def _build_stub_output(self, context: ModelInvocationContext) -> str:
        task_name = context.task_name

        if task_name == "primary_canonical_extraction":
            return self._primary_extraction_output()

        if task_name == "judge_canonical_extraction":
            return self._judge_output(candidate_text=context.user_input)

        if task_name == "fallback_canonical_extraction":
            return self._fallback_extraction_output()

        return '{"message": "No stub output configured for this task."}'

    def _primary_extraction_output(self) -> str:
        """
        Simula la salida del extractor principal.
        """
        return (
            "{"
            '"incident_case": {'
            '"source_type": "sms_bitacora", '
            '"header": "STUB HEADER", '
            '"failure_text": "STUB FAILURE", '
            '"impact_text": "STUB IMPACT", '
            '"start_time": null, '
            '"incident_status": "closed", '
            '"raw_sms": "STUB RAW SMS", '
            '"probable_cause_text": null, '
            '"resolution_summary": null, '
            '"component_types": [], '
            '"components_affected": [], '
            '"services_affected": [], '
            '"symptoms": [], '
            '"teams_involved": [], '
            '"tickets": [], '
            '"tags": []'
            "}, "
            '"timeline_entries": [], '
            '"troubleshooting_actions": [], '
            '"extraction_metadata": {'
            '"extractor_name": "stub_primary_extractor", '
            '"extractor_version": "v1", '
            '"model_name": "stub-primary-model", '
            '"rulebook_path": "app/agentic/rules/incident_extraction_rules.md", '
            '"rulebook_version": "v1", '
            '"confidence_notes": [], '
            '"warnings": []'
            "}"
            "}"
        )

    def _fallback_extraction_output(self) -> str:
        """
        Simula la salida del extractor fallback.
        Incluye la palabra FALLBACK en varios campos para que el juez stub
        pueda detectar que está evaluando la segunda propuesta.
        """
        return (
            "{"
            '"incident_case": {'
            '"source_type": "sms_bitacora", '
            '"header": "STUB HEADER FALLBACK", '
            '"failure_text": "STUB FAILURE FALLBACK", '
            '"impact_text": "STUB IMPACT FALLBACK", '
            '"start_time": null, '
            '"incident_status": "closed", '
            '"raw_sms": "STUB RAW SMS FALLBACK", '
            '"probable_cause_text": null, '
            '"resolution_summary": null, '
            '"component_types": [], '
            '"components_affected": [], '
            '"services_affected": [], '
            '"symptoms": [], '
            '"teams_involved": [], '
            '"tickets": [], '
            '"tags": []'
            "}, "
            '"timeline_entries": [], '
            '"troubleshooting_actions": [], '
            '"extraction_metadata": {'
            '"extractor_name": "stub_fallback_extractor", '
            '"extractor_version": "v1", '
            '"model_name": "stub-fallback-model", '
            '"rulebook_path": "app/agentic/rules/incident_extraction_rules.md", '
            '"rulebook_version": "v1", '
            '"confidence_notes": [], '
            '"warnings": []'
            "}"
            "}"
        )

    def _judge_output(self, candidate_text: str | None = None) -> str:
        """
        Simula la decisión del juez según el escenario configurado.

        Escenarios soportados:
        - happy_path:
            el juez acepta de inmediato
        - reject_then_accept:
            el juez rechaza la propuesta principal, pero acepta la fallback
        - reject_twice:
            el juez rechaza tanto la propuesta principal como la fallback

        La detección de fallback se hace buscando la palabra 'FALLBACK'
        en el texto de la propuesta evaluada.
        """
        if self._scenario == "happy_path":
            return (
                "{"
                '"decision": "accepted", '
                '"feedback": "Stub judge accepted the extraction."'
                "}"
            )

        if self._scenario == "reject_then_accept":
            if candidate_text and "FALLBACK" in candidate_text.upper():
                return (
                    "{"
                    '"decision": "accepted", '
                    '"feedback": "Fallback extraction accepted by stub judge."'
                    "}"
                )
            return (
                "{"
                '"decision": "rejected", '
                '"feedback": "Primary extraction rejected: missing or weak fields."'
                "}"
            )

        if self._scenario == "reject_twice":
            return (
                "{"
                '"decision": "rejected", '
                '"feedback": "Extraction rejected: insufficient quality."'
                "}"
            )

        return (
            "{"
            '"decision": "accepted_with_observations", '
            '"feedback": "Default stub decision with observations."'
            "}"
        )
