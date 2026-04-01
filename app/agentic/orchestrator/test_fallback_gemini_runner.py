from app.agentic.prompts import (
    PromptSettings,
    build_fallback_extractor_system_prompt,
    build_fallback_extractor_user_prompt,
)
from app.agentic.providers.gemini_model_gateway import GeminiModelGateway
from app.agentic.providers.provider_models import ModelInvocationContext
from app.core.config import settings


def main() -> None:
    """
    Runner para probar solo el fallback con Gemini.

    Este runner valida:
    - construcción del prompt del fallback
    - uso del rulebook específico del fallback
    - incorporación de extracción previa rechazada
    - incorporación de feedback del juez
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

    previous_extraction_text = """
{
  "incident_case": {
    "source_type": "sms_bitacora",
    "header": "NOC DATACENTER-TI",
    "failure_text": "Evento de carga en BD XXXXXXXX 09/02/2026 07:45 hrs.",
    "impact_text": "Errores técnicos en los microservicios del APP XXXX y disminución de transacciones en XXX Postpago.",
    "incident_status": "closed",
    "raw_sms": "NOC DATACENTER-TI ...",
    "probable_cause_text": "Sobrecarga en base de datos",
    "resolution_summary": "DBA resolvió el problema",
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
      "sequence_order": 1
    }
  ],
  "troubleshooting_actions": [
    {
      "action_text": "NOC TI confirma estabilidad de los servicios.",
      "action_type": "remediation",
      "action_role": "remediation",
      "target_component": "database",
      "sequence_order": 1
    }
  ],
  "extraction_metadata": {
    "extractor_name": "primary_extractor",
    "extractor_version": "v1",
    "model_name": "gemini-3.1-flash-lite-preview",
    "confidence_notes": ["Extracción basada en etiquetas claras."],
    "warnings": [],
    "missing_fields": [],
    "inferred_fields": ["probable_cause_text", "resolution_summary"]
  }
}
""".strip()

    judge_feedback_text = """
La propuesta identifica correctamente el impacto y el ticket, pero inventa una causa raíz no respaldada por el SMS y también afirma una resolución técnica no explícita. 
Debe dejar `probable_cause_text` vacío, dejar `resolution_summary` vacío o fiel al documento, y no clasificar la confirmación de estabilidad como una remediación efectiva.
También debe incorporar el hito explícito de las 08:05 hrs como hora de solución.
""".strip()

    prompt_settings = PromptSettings(
        extraction_rulebook_path="app/agentic/rules/incident_extraction_rules.md",
        extraction_rulebook_version="v1",
        judge_rulebook_path="app/agentic/rules/judge_extraction_rules.md",
        judge_rulebook_version="v1",
        fallback_rulebook_path="app/agentic/rules/fallback_extraction_rules.md",
        fallback_rulebook_version="v1",
        enforce_rulebook_usage=True,
        extra_instruction=(
            "Devuelve únicamente JSON válido compatible con el contrato canónico. "
            "Debes corregir explícitamente los problemas señalados por el juez, "
            "sin inventar nueva información. "
            "No agregues markdown ni texto fuera del JSON."
        ),
        judge_strict_mode=True,
    )

    gateway = GeminiModelGateway()

    response_schema = {
        "type": "OBJECT",
        "properties": {
            "incident_case": {
                "type": "OBJECT",
                "properties": {
                    "source_type": {"type": "STRING"},
                    "header": {"type": "STRING"},
                    "failure_text": {"type": "STRING"},
                    "impact_text": {"type": "STRING"},
                    "incident_status": {"type": "STRING"},
                    "raw_sms": {"type": "STRING"},
                    "probable_cause_text": {"type": "STRING"},
                    "resolution_summary": {"type": "STRING"},
                    "component_types": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "components_affected": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "services_affected": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "symptoms": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "teams_involved": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "tickets": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "tags": {"type": "ARRAY", "items": {"type": "STRING"}}
                },
                "required": [
                    "source_type",
                    "failure_text",
                    "incident_status",
                    "raw_sms",
                    "component_types",
                    "components_affected",
                    "services_affected",
                    "symptoms",
                    "teams_involved",
                    "tickets",
                    "tags"
                ]
            },
            "timeline_entries": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "event_time": {"type": "STRING"},
                        "event_text": {"type": "STRING"},
                        "sequence_order": {"type": "INTEGER"}
                    },
                    "required": ["event_text", "sequence_order"]
                }
            },
            "troubleshooting_actions": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "action_text": {"type": "STRING"},
                        "action_type": {"type": "STRING"},
                        "action_role": {"type": "STRING"},
                        "target_component": {"type": "STRING"},
                        "sequence_order": {"type": "INTEGER"}
                    },
                    "required": ["action_text", "sequence_order"]
                }
            },
            "extraction_metadata": {
                "type": "OBJECT",
                "properties": {
                    "extractor_name": {"type": "STRING"},
                    "extractor_version": {"type": "STRING"},
                    "model_name": {"type": "STRING"},
                    "confidence_notes": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "warnings": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "missing_fields": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "inferred_fields": {"type": "ARRAY", "items": {"type": "STRING"}}
                },
                "required": [
                    "extractor_name",
                    "extractor_version",
                    "confidence_notes",
                    "warnings",
                    "missing_fields",
                    "inferred_fields"
                ]
            }
        },
        "required": [
            "incident_case",
            "timeline_entries",
            "troubleshooting_actions",
            "extraction_metadata"
        ]
    }

    context = ModelInvocationContext(
        system_instruction=build_fallback_extractor_system_prompt(prompt_settings),
        user_input=build_fallback_extractor_user_prompt(
            raw_sms=raw_sms,
            previous_extraction_text=previous_extraction_text,
            judge_feedback_text=judge_feedback_text,
        ),
        task_name="fallback_canonical_extraction",
        model_name=settings.agentic_models.fallback_extractor_model,
        temperature=0.2,
        extra_config={
            "response_mime_type": "application/json",
            "response_schema": response_schema,
        },
    )

    response = gateway.invoke(context)

    print("\n=== FALLBACK GEMINI RESPONSE ===")
    print(f"provider_name: {response.provider_name}")
    print(f"model_name: {response.model_name}")
    print("\n--- OUTPUT TEXT START ---\n")
    print(response.output_text)
    print("\n--- OUTPUT TEXT END ---\n")


if __name__ == "__main__":
    main()
