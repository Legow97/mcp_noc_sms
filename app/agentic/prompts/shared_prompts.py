from pathlib import Path

from app.agentic.prompts.prompt_settings import PromptSettings


def load_rulebook_text(rulebook_path: str) -> str:
    """
    Carga el contenido de un rulebook desde archivo.
    """
    path = Path(rulebook_path)

    if not path.exists():
        return (
            "RULEBOOK_NOT_FOUND: No se encontró el archivo de reglas. "
            "Continúa con máxima prudencia y evita inferencias débiles."
        )

    return path.read_text(encoding="utf-8")


def build_rulebook_context(
    *,
    subsystem_role: str,
    rulebook_path: str,
    rulebook_version: str,
    settings: PromptSettings,
) -> str:
    """
    Construye el bloque común de contexto para prompts que usan un rulebook.

    Permite reutilizar la misma función para:
    - extractor principal
    - juez
    - fallback
    """
    rulebook_text = load_rulebook_text(rulebook_path)

    shared_parts = [
        "Eres parte del subsistema Canonical Extraction Service.",
        f"Rol actual del subsistema: {subsystem_role}.",
        f"Rulebook version: {rulebook_version}",
    ]

    if settings.enforce_rulebook_usage:
        shared_parts.append(
            "Debes seguir estrictamente el rulebook proporcionado y evitar "
            "inventar información no respaldada."
        )

    if settings.extra_instruction.strip():
        shared_parts.append(f"Instrucción adicional: {settings.extra_instruction.strip()}")

    shared_parts.append("\n=== RULEBOOK START ===\n")
    shared_parts.append(rulebook_text)
    shared_parts.append("\n=== RULEBOOK END ===")

    return "\n".join(shared_parts)