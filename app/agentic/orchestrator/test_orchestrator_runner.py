from app.agentic.orchestrator import CanonicalExtractionOrchestrator
from app.agentic.prompts import PromptSettings
from app.agentic.providers import StubModelGateway


def main() -> None:
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
        extra_instruction="Sé conservador con inferencias de causa y remediación.",
        judge_strict_mode=True,
    )

    gateway = StubModelGateway(
        provider_name="stub_provider",
        default_model_name="stub-generic-model",
        scenario="happy_path",
    )

    orchestrator = CanonicalExtractionOrchestrator(
        model_gateway=gateway,
        prompt_settings=prompt_settings,
    )

    result = orchestrator.extract(raw_sms)

    print("\n=== ORCHESTRATION RESULT ===")
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()