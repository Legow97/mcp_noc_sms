from app.agentic.orchestrator import CanonicalExtractionOrchestrator
from app.agentic.prompts import PromptSettings
from app.agentic.providers.gemini_model_gateway import GeminiModelGateway


def main() -> None:
    """
    Runner del flujo real completo:
    - extractor principal real
    - juez real
    - fallback real (solo si aplica)
    - juez final real
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
        extraction_rulebook_path="app/agentic/rules/incident_extraction_rules.md",
        extraction_rulebook_version="v1",
        judge_rulebook_path="app/agentic/rules/judge_extraction_rules.md",
        judge_rulebook_version="v1",
        fallback_rulebook_path="app/agentic/rules/fallback_extraction_rules.md",
        fallback_rulebook_version="v1",
        enforce_rulebook_usage=True,
        extra_instruction=(
            "Devuelve únicamente JSON válido y compatible con los contratos internos "
            "del subsistema. No agregues markdown ni texto fuera del JSON."
        ),
        judge_strict_mode=True,
    )

    gateway = GeminiModelGateway()

    orchestrator = CanonicalExtractionOrchestrator(
        model_gateway=gateway,
        prompt_settings=prompt_settings,
    )

    result = orchestrator.extract(raw_sms)

    print("\n=== FULL GEMINI ORCHESTRATION RESULT ===")
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()