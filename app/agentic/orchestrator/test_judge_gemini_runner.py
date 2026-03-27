from app.agentic.prompts import (
    PromptSettings,
    build_judge_system_prompt,
    build_judge_user_prompt,
)
from app.agentic.providers.gemini_model_gateway import GeminiModelGateway
from app.agentic.providers.provider_models import ModelInvocationContext
from app.core.config import settings


def main() -> None:
    """
    Runner para probar solo el juez con Gemini.

    Este runner valida:
    - construcción del prompt del juez
    - uso del rulebook específico del juez
    - invocación real del modelo juez
    - recepción de salida JSON estructurada
    """

    raw_sms = """
NOC DATACENTER-TI

FALLA: Evento de carga en BD XXXXXXXX 09/02/2026 07:45 hrs.

IMPACTO:
-Errores técnicos en los microservicios del APP XXXX y disminución de transacciones en XXX Postpago.

SOLUCIONADO:
* 07:55 hrs Se reporta a Soporte DBA con ticket INC000000123456.
* 08:40 hrs NOC TI confirma estabilidad de los servicios. Se cierra SMS.

HORA DE SOLUCIÓN: 09/02/2026 08:05 hrs.
""".strip()

    candidate_extraction_text = """
{
  "incident_case": {
    "source_type": "sms_bitacora",
    "header": "NOC DATACENTER-TI",
    "failure_text": "Evento de carga en BD XXXXXXXX 09/02/2026 07:45 hrs.",
    "impact_text": "Errores técnicos en los microservicios del APP XXXX y disminución de transacciones en XXX Postpago.",
    "incident_status": "closed",
    "pending_rca": true,
    "raw_sms": "NOC DATACENTER-TI ...",
    "probable_cause_text": null,
    "resolution_summary": null,
    "component_types": [],
    "components_affected": [],
    "services_affected": [],
    "symptoms": [],
    "teams_involved": ["Soporte DBA", "NOC TI"],
    "tickets": ["INC000000123456"],
    "tags": []
  },
  "timeline_entries": [
    {
      "event_time": "07:55 hrs",
      "event_text": "Se reporta a Soporte DBA con ticket INC000000123456.",
      "event_type": "action",
      "team": "Soporte DBA",
      "action_detected": "report_to_dba",
      "observation_detected": null,
      "sequence_order": 1
    },
    {
      "event_time": "08:40 hrs",
      "event_text": "NOC TI confirma estabilidad de los servicios. Se cierra SMS.",
      "event_type": "closure",
      "team": "NOC TI",
      "action_detected": null,
      "observation_detected": "service_stability_confirmed",
      "sequence_order": 2
    }
  ],
  "troubleshooting_actions": [
    {
      "action_text": "Se reporta a Soporte DBA con ticket INC000000123456.",
      "action_type": "escalation",
      "action_role": "coordination",
      "target_component": "database",
      "outcome": null,
      "was_effective": null,
      "sequence_order": 1
    }
  ],
  "extraction_metadata": {
    "extractor_name": "primary_extractor",
    "extractor_version": "v1",
    "model_name": "gemini-3.1-flash-lite-preview",
    "confidence_notes": ["Extracción basada en etiquetas claras."],
    "warnings": ["No se identifica causa raíz explícita."],
    "missing_fields": ["probable_cause_text", "resolution_summary"],
    "inferred_fields": ["incident_status", "pending_rca"]
  }
}
""".strip()

    prompt_settings = PromptSettings(
        extraction_rulebook_path="app/agentic/rules/incident_extraction_rules.md",
        extraction_rulebook_version="v1",
        judge_rulebook_path="app/agentic/rules/judge_extraction_rules.md",
        judge_rulebook_version="v1",
        enforce_rulebook_usage=True,
        extra_instruction=(
            "Devuelve únicamente JSON válido. "
            "La salida del juez debe incluir: decision, score, score_breakdown, "
            "critical_issues, strengths, issues, improvement_actions y feedback. "
            "Usa la escala de puntuación definida por el rulebook del juez. "
            "No agregues markdown ni texto fuera del JSON."
        ),
        judge_strict_mode=True,
    )

    gateway = GeminiModelGateway()

    response_schema = {
        "type": "OBJECT",
        "properties": {
            "decision": {
                "type": "STRING",
                "enum": [
                    "accepted",
                    "accepted_with_observations",
                    "rejected",
                ],
            },
            "score": {"type": "NUMBER"},
            "score_breakdown": {
                "type": "OBJECT",
                "properties": {
                    "fidelity": {"type": "NUMBER"},
                    "coverage": {"type": "NUMBER"},
                    "structural_classification": {"type": "NUMBER"},
                    "semantic_prudence": {"type": "NUMBER"},
                    "metadata_quality": {"type": "NUMBER"},
                },
                "required": [
                    "fidelity",
                    "coverage",
                    "structural_classification",
                    "semantic_prudence",
                    "metadata_quality",
                ],
            },
            "critical_issues": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            "strengths": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            "issues": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            "improvement_actions": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            "feedback": {"type": "STRING"},
        },
        "required": [
            "decision",
            "score",
            "score_breakdown",
            "critical_issues",
            "strengths",
            "issues",
            "improvement_actions",
            "feedback",
        ],
    }

    context = ModelInvocationContext(
        system_instruction=build_judge_system_prompt(prompt_settings),
        user_input=build_judge_user_prompt(
            raw_sms=raw_sms,
            candidate_extraction_text=candidate_extraction_text,
        ),
        task_name="judge_canonical_extraction",
        model_name=settings.agentic_models.semantic_judge_model,
        temperature=0.1,
        extra_config={
            "response_mime_type": "application/json",
            "response_schema": response_schema,
        },
    )

    response = gateway.invoke(context)

    print("\n=== JUDGE GEMINI RESPONSE ===")
    print(f"provider_name: {response.provider_name}")
    print(f"model_name: {response.model_name}")
    print("\n--- OUTPUT TEXT START ---\n")
    print(response.output_text)
    print("\n--- OUTPUT TEXT END ---\n")


if __name__ == "__main__":
    main()