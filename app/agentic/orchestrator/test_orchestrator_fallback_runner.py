from app.agentic.orchestrator import CanonicalExtractionOrchestrator
from app.agentic.prompts import PromptSettings
from app.agentic.providers import StubModelGateway


def main() -> None:
    raw_sms = """
⚠️⚠️⚠️ REQ000000012345 - CLARO TE RECOMIENDA - INCONVENIENTES CON EL ACCESO ⚠️⚠️⚠️

📋TICKET:
-REQ000000012345

☀️ IMPACTO
- INCONVENIENTES CON EL ACCESO
- SIN TRANSACCIONES DENTRO DEL PORTAL

⚒️ACCIONES:
7:16 hrs. Se apertura sala TEAMS para la revisión.
8:06 hrs. Se autoriza el rollback.
8:13 hrs. Se indica el término del rollback.

🔎CAUSA
- Error 403 en DATAPOWER.

✅SOLUCIÓN
- ROLLBACK DEL TAS000000012345 - DATAPOWER
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
        scenario="reject_then_accept",
    )

    orchestrator = CanonicalExtractionOrchestrator(
        model_gateway=gateway,
        prompt_settings=prompt_settings,
    )

    result = orchestrator.extract(raw_sms)

    print("\n=== FALLBACK ORCHESTRATION RESULT ===")
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()