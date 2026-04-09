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
        self._prompts_dir = Path(prompts_dir)
        self._prompt_files = prompt_files or [
            "reasoning_agent_system.md",
            "response_policy.md",
        ]

    def load_system_instruction(self) -> str:
        sections: list[str] = []

        for prompt_file in self._prompt_files:
            prompt_path = self._prompts_dir / prompt_file
            sections.append(prompt_path.read_text(encoding="utf-8").strip())

        return "\n\n".join(section for section in sections if section)
