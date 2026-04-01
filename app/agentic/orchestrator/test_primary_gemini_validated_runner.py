from app.agentic.orchestrator.response_parsers import parse_extraction_response
from app.agentic.prompts import (
    PromptSettings,
    build_primary_extractor_system_prompt,
    build_primary_extractor_user_prompt,
)
from app.agentic.providers.gemini_model_gateway import GeminiModelGateway
from app.agentic.providers.provider_models import ModelInvocationContext
from app.core.config import settings


def main() -> None:
    """
    Runner para probar el extractor principal con Gemini y validar
    la salida contra CanonicalExtractionResult.
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

    prompt_settings = PromptSettings(
        rulebook_path="app/agentic/rules/incident_extraction_rules.md",
        rulebook_version="v1",
        enforce_rulebook_usage=True,
        extra_instruction=(
                "Devuelve únicamente JSON válido compatible con el contrato canónico. "
                "En extraction_metadata: "
                "extractor_name debe ser 'primary_extractor', "
                "extractor_version debe ser una versión lógica simple como 'v1', "
                "model_name debe reflejar el modelo LLM usado, "
                "y no debes incluir rulebook_path ni rulebook_version. "
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
                    "tags": {"type": "ARRAY", "items": {"type": "STRING"}},
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
                    "tags",
                ],
            },
            "timeline_entries": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "event_time": {"type": "STRING"},
                        "event_text": {"type": "STRING"},
                        "sequence_order": {"type": "INTEGER"},
                    },
                    "required": ["event_text", "sequence_order"],
                },
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
                        "sequence_order": {"type": "INTEGER"},
                    },
                    "required": ["action_text", "sequence_order"],
                },
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
                    "inferred_fields": {"type": "ARRAY", "items": {"type": "STRING"}},
                },
                "required": [
                    "extractor_name",
                    "extractor_version",
                    "confidence_notes",
                    "warnings",
                    "missing_fields",
                    "inferred_fields",
                ],
            },
        },
        "required": [
            "incident_case",
            "timeline_entries",
            "troubleshooting_actions",
            "extraction_metadata",
        ],
    }

    context = ModelInvocationContext(
        system_instruction=build_primary_extractor_system_prompt(prompt_settings),
        user_input=build_primary_extractor_user_prompt(raw_sms),
        task_name="primary_canonical_extraction",
        model_name=settings.agentic_models.primary_extractor_model,
        temperature=0.2,
        extra_config={
            "response_mime_type": "application/json",
            "response_schema": response_schema,
        },
    )

    raw_response = gateway.invoke(context)

    print("\n=== RAW MODEL OUTPUT ===\n")
    print(raw_response.output_text)

    validated_result = parse_extraction_response(raw_response)

    print("\n=== VALIDATED CANONICAL EXTRACTION RESULT ===\n")
    print(validated_result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
