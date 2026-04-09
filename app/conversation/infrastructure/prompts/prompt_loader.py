from __future__ import annotations

from pathlib import Path


class MarkdownPromptLoader:
    """
    Carga instrucciones del agente desde archivos markdown.
    """

    def __init__(
        self,
        prompts_dir: str,
        prompt_files: list[str] | None = None,
    ) -> None:
        self._prompts_dir = self._resolve_prompts_dir(prompts_dir)
        self._prompt_files = prompt_files or self._resolve_default_prompt_files()

    def load_system_instruction(self) -> str:
        sections: list[str] = []

        for prompt_file in self._prompt_files:
            prompt_path = self._prompts_dir / prompt_file
            sections.append(prompt_path.read_text(encoding="utf-8").strip())

        return "\n\n".join(section for section in sections if section)

    def _resolve_default_prompt_files(self) -> list[str]:
        prompt_files = [
            "reasoning_agent_system.md",
            "response_policy.md",
        ]
        external_policy_file = "external_research_policy.md"
        if (self._prompts_dir / external_policy_file).exists():
            prompt_files.append(external_policy_file)
        return prompt_files

    def _resolve_prompts_dir(self, prompts_dir: str) -> Path:
        configured_dir = Path(prompts_dir)
        if configured_dir.exists():
            return configured_dir

        conversation_root = Path(__file__).resolve().parents[2]
        legacy_relative_dir = Path("app/conversation/prompts")
        legacy_absolute_dir = conversation_root / "prompts"
        configured_dir_normalized = configured_dir.as_posix()

        if configured_dir == legacy_relative_dir or (
            configured_dir_normalized.endswith("app/conversation/prompts")
            and configured_dir_normalized != legacy_absolute_dir.as_posix()
        ) or configured_dir == legacy_absolute_dir:
            return conversation_root / "config" / "prompts"

        return configured_dir
