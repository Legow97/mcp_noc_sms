from __future__ import annotations

from collections.abc import Iterable

from app.conversation.application.reasoning.execution_context import (
    ConversationExecutionContext,
)
from app.conversation.application.skills.base import (
    ConversationSkill,
    SkillExecutionStatus,
    SkillResult,
)


class SkillRegistry:
    """Registro simple para activar o reemplazar skills sin tocar el núcleo."""

    def __init__(self, skills: Iterable[ConversationSkill] | None = None) -> None:
        self._skills = {skill.name: skill for skill in skills or []}

    def register(self, skill: ConversationSkill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> ConversationSkill | None:
        return self._skills.get(name)

    def invoke(self, name: str, context: ConversationExecutionContext) -> SkillResult:
        skill = self.get(name)
        if skill is None:
            return SkillResult(
                skill_name=name,
                status=SkillExecutionStatus.FAILED,
                errors=[f"Skill not registered: {name}"],
            )

        if not skill.is_enabled(context):
            return SkillResult(
                skill_name=name,
                status=SkillExecutionStatus.DISABLED,
                summary=f"Skill {name} disabled for current context.",
            )

        return skill.execute(context)

    def list_names(self) -> list[str]:
        return sorted(self._skills)
