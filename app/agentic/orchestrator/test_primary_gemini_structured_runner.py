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
    Runner para probar el extractor principal con Gemini pidiendo JSON estructurado.
    """

    raw_sms = """______________
⚠️⚠️⚠️ REQ0000000XXXX  - CLARO TE RECOMIENDA - INCONVENIENTES CON EL ACCESO ⚠️⚠️⚠️
______________

📋TICKET: 

 -REQ0000000XXXX


☀️ IMPACTO

- INCONVENIENTES CON EL ACCESO 
- SIN TRANSACCIONES DENTRO DEL PORTAL

⚒️ACCIONES:

7:16 hrs. Se apertura sala TEAMS para la revisión.
7:18 hrs. Sube el equipo de SOAP XXXXX POSTVENTAS.
7:21 hrs. Se informa que el impacto es masivo ya que no se puede acceder a la web
7:23 hrs. SOAP XXXXX POSTVENTAS indica que están revisando logs para mayores descarte.
7:32 hrs. SOAP XXXXX INTEGRACION sube a sala para mayor descarte de un servidor (error en datapower) - http://172.19.XXX.X:XXX/v1.0/plataforma-XXXXXXX/enterprise_Domain/administrative/registroAuditoria/registroAuditoria
7:34 hrs. SOAP XXXXX INTEGRACION revisa que los siguientes servidores 172.20.219.85 | 172.20.219.84 | 172.19.98.94 | 172.19.98.93 por indicación del equipo SOAP HITSS POSTVENTA. 
7:36 hrs. SOAP XXXXX INTEGRACION indica que hoy en madrugada han sido modificados y se requiere de mayor información sobre los pases.
7:42 hrs. Se revisa los pases (TAS0000000XXXXX) de madrugada y se verifica que dichas IPS 172.20.219.85 | 172.20.219.84 | 172.19.98.94 | 172.19.98.93 han sido retiradas.
Se pedirá el rollback al PAP.
7:50 hrs. SOAP XXXXX POSTVENTAS formaliza la revisión de las IPS 172.20.219.85 | 172.20.219.84 | 172.19.98.94 | 172.19.98.93 | 172.20.219.83 | 172.20.219.82 | 172.19.98.92 | 172.19.98.91 mediante correo al equipo de INTEGRACION para que luego ser revisado por el PAP solicitando rollback.
7:56 hrs. SOAP XXXXX INTEGRACION envia correo al SOAP CLARO INTEGRACION para que aprueba el rollback del pase TAS0000000XXXXX  
8:06 hrs. SOAP XXXXX INTEGRACION autoriza el rollback de TAS0000000XXXXX - DATAPOWER , Equipo PAP sube a sala y procederá con la ejecución.
8:13 hrs. EQUIPO PAP XXXXX indica el termino del rollback , SOAP XXXXX POSTVENTAS valida el acceso a la web. Se pide a ATU validar con los usuarios.
8:26 hrs. Se da la conformidad por parte del equipo ATU en consulta con los usuarios, se finaliza sala.
 
🔎CAUSA

- Error 403 en DATAPOWER debido al pase TAS0000000XXXXX donde las siguientes IPS han sido retiradas | IPS 172.20.XX.XX | 172.20.XX.XX | 172.19.YY.YY | 172.19.XX.XX 

✅SOLUCIÓN

- ROLLBACK DEL TAS0000000XXXXX -DATAPOWER


⏰FECHA/H.Inicio: 13/03/2026 7:16 hrs.
⏰FECHA/H.Fin:    13/03/2026 8:13 hrs.


""".strip()

    prompt_settings = PromptSettings(
        rulebook_path="app/agentic/rules/incident_extraction_rules.md",
        rulebook_version="v1",
        enforce_rulebook_usage=True,
        extra_instruction=(
            "Devuelve únicamente JSON válido compatible con el contrato canónico. "
            "No agregues markdown, explicación ni texto fuera del JSON."
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
                    "pending_rca": {"type": "BOOLEAN"},
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
                    "pending_rca",
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
                        "event_type": {"type": "STRING"},
                        "team": {"type": "STRING"},
                        "action_detected": {"type": "STRING"},
                        "observation_detected": {"type": "STRING"},
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
                        "outcome": {"type": "STRING"},
                        "was_effective": {"type": "BOOLEAN"},
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
                    "rulebook_path": {"type": "STRING"},
                    "rulebook_version": {"type": "STRING"},
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

    response = gateway.invoke(context)

    print("\n=== PRIMARY GEMINI STRUCTURED RESPONSE ===")
    print(f"provider_name: {response.provider_name}")
    print(f"model_name: {response.model_name}")
    print("\n--- OUTPUT TEXT START ---\n")
    print(response.output_text)
    print("\n--- OUTPUT TEXT END ---\n")


if __name__ == "__main__":
    main()