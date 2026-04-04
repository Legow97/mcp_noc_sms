from __future__ import annotations

from datetime import datetime

from app.services.retrieval.incident_retrieval_source_reader import (
    IncidentRetrievalSourceData,
)


class IncidentRetrievalDocumentBuilder:
    """
    Ensambla document_text_v1 exclusivamente a partir de data persistida.
    """

    def build(self, source_data: IncidentRetrievalSourceData) -> dict[str, str]:
        incident_case = source_data.incident_case
        lines: list[str] = []

        self._append_field(lines, "Case ID", incident_case.case_id)
        self._append_field(lines, "Start Time", self._format_datetime(incident_case.start_time))
        self._append_field(lines, "Header", incident_case.header)
        self._append_field(lines, "Failure", incident_case.failure_text)
        self._append_field(lines, "Impact", incident_case.impact_text)
        self._append_field(
            lines,
            "Services Affected",
            self._join_stable_values(incident_case.services_affected),
        )
        self._append_field(
            lines,
            "Components Affected",
            self._join_stable_values(incident_case.components_affected),
        )
        self._append_section(
            lines,
            "Timeline",
            [
                self._format_timeline_entry(entry.event_time, entry.event_text)
                for entry in sorted(
                    source_data.timeline_entries,
                    key=lambda item: item.sequence_order,
                )
            ],
        )
        self._append_field(
            lines,
            "Solution Time",
            self._format_datetime(incident_case.solution_time),
        )
        self._append_section(
            lines,
            "Troubleshooting Actions",
            [
                self._format_troubleshooting_action(
                    sequence_order=action.sequence_order,
                    action_text=action.action_text,
                    action_type=action.action_type,
                )
                for action in sorted(
                    source_data.troubleshooting_actions,
                    key=lambda item: item.sequence_order,
                )
            ],
        )
        self._append_field(
            lines,
            "Probable Cause",
            incident_case.probable_cause_text,
        )
        self._append_field(
            lines,
            "Resolution Summary",
            incident_case.resolution_summary,
        )
        self._append_field(
            lines,
            "Tags",
            self._join_stable_values(incident_case.tags),
        )

        return {
            "case_id": incident_case.case_id,
            "document_text": "\n".join(lines),
        }

    def _append_field(
        self,
        lines: list[str],
        label: str,
        value: str | None,
    ) -> None:
        normalized_value = self._clean_text(value)
        if normalized_value is None:
            return

        lines.append(f"{label}: {normalized_value}")

    def _append_section(
        self,
        lines: list[str],
        title: str,
        items: list[str | None],
    ) -> None:
        rendered_items = [item for item in items if self._clean_text(item) is not None]
        if not rendered_items:
            return

        lines.append(f"{title}:")
        lines.extend(rendered_items)

    def _format_timeline_entry(
        self,
        event_time: str | None,
        event_text: str | None,
    ) -> str | None:
        parts = [
            part
            for part in (
                self._clean_text(event_time),
                self._clean_text(event_text),
            )
            if part is not None
        ]
        if not parts:
            return None

        return f"- {' - '.join(parts)}"

    def _format_troubleshooting_action(
        self,
        *,
        sequence_order: int | None,
        action_text: str | None,
        action_type: str | None,
    ) -> str | None:
        parts = [
            str(sequence_order) if sequence_order is not None else None,
            self._clean_text(action_text),
            self._clean_text(action_type),
        ]
        rendered_parts = [part for part in parts if part is not None]
        if not rendered_parts:
            return None

        return f"- {' - '.join(rendered_parts)}"

    def _join_stable_values(self, values: list[str]) -> str | None:
        normalized_values: list[str] = []
        seen: set[str] = set()

        for value in values:
            normalized = self._clean_text(value)
            if normalized is None or normalized in seen:
                continue
            seen.add(normalized)
            normalized_values.append(normalized)

        if not normalized_values:
            return None

        return ", ".join(normalized_values)

    def _format_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None

        return value.isoformat()

    def _clean_text(self, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None
