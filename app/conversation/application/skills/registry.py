from __future__ import annotations

from collections.abc import Iterable

from app.conversation.application.skills.base import ConversationSkill


class SkillRegistry:
    """Registro simple para activar o reemplazar skills sin tocar el núcleo."""

    def __init__(self, skills: Iterable[ConversationSkill] | None = None) -> None:
        self._skills = {skill.name: skill for skill in skills or []}

    def register(self, skill: ConversationSkill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> ConversationSkill | None:
        return self._skills.get(name)

    def list_names(self) -> list[str]:
        return sorted(self._skills)
