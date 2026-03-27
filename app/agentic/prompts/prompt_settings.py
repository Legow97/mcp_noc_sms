from dataclasses import dataclass


@dataclass(slots=True)
class PromptSettings:
    """
    Configuración editable de prompts del subsistema agentic.

    La idea es que puedas ajustar fácilmente:
    - rulebooks por rol
    - versiones lógicas
    - tono
    - nivel de rigor
    - instrucciones extra

    sin tocar directamente la lógica del orquestador.
    """


    extraction_rulebook_path: str = "app/agentic/rules/incident_extraction_rules.md"
    extraction_rulebook_version: str = "v1"

    judge_rulebook_path: str = "app/agentic/rules/judge_extraction_rules.md"
    judge_rulebook_version: str = "v1"

    fallback_rulebook_path: str = "app/agentic/rules/fallback_extraction_rules.md"
    fallback_rulebook_version: str = "v1"

    enforce_rulebook_usage: bool = True
    extra_instruction: str = ""
    judge_strict_mode: bool = True