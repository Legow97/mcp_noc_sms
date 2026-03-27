from app.agentic.prompts import (
    PromptSettings,
    build_primary_extractor_system_prompt,
    build_primary_extractor_user_prompt,
)
from app.agentic.providers.openai_compatible_model_gateway import (
    OpenAICompatibleModelGateway,
)
from app.agentic.providers.provider_models import ModelInvocationContext
from app.core.config import settings


def main() -> None:
    """
    Runner para probar solo el extractor principal con provider real.

    Este runner sirve para validar:
    - conexión al backend compatible con OpenAI
    - autenticación
    - modelo configurado
    - construcción de prompts
    - recepción de salida textual real
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
        extra_instruction="Devuelve una extracción fiel, conservadora y compatible con el contrato canónico.",
        judge_strict_mode=True,
    )

    gateway = OpenAICompatibleModelGateway()

    context = ModelInvocationContext(
        system_instruction=build_primary_extractor_system_prompt(prompt_settings),
        user_input=build_primary_extractor_user_prompt(raw_sms),
        task_name="primary_canonical_extraction",
        model_name=settings.agentic_models.primary_extractor_model,
        temperature=0.2,
    )

    response = gateway.invoke(context)

    print("\n=== PRIMARY REAL MODEL RESPONSE ===")
    print(f"provider_name: {response.provider_name}")
    print(f"model_name: {response.model_name}")
    print("\n--- OUTPUT TEXT START ---\n")
    print(response.output_text)
    print("\n--- OUTPUT TEXT END ---\n")


if __name__ == "__main__":
    main()