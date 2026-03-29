from __future__ import annotations

from dataclasses import dataclass

from app.agentic.contracts.canonical_extraction import (
    CanonicalExtractionResult,
    CanonicalTimelineEntryData,
    CanonicalTroubleshootingActionData,
)
from app.core.temporal import parse_incident_datetime
from app.db.models import (
    IncidentCaseModel,
    IncidentTimelineEntryModel,
    TroubleshootingActionModel,
)


@dataclass(slots=True)
class CanonicalExtractionPersistenceBundle:
    incident_case: IncidentCaseModel
    timeline_entries: list[IncidentTimelineEntryModel]
    troubleshooting_actions: list[TroubleshootingActionModel]


class CanonicalExtractionMapper:
    def to_persistence_bundle(
        self,
        extraction: CanonicalExtractionResult,
        *,
        case_id: str,
        judge_evaluation: dict | None = None,
        trace: object | None = None,
    ) -> CanonicalExtractionPersistenceBundle:
        print(
            "[MAPPER] build_bundle entrada:",
            {
                "case_id": case_id,
                "extraction": extraction.model_dump(mode="json"),
                "judge_evaluation": judge_evaluation,
                "trace": trace,
            },
        )
        incident_case = self.build_incident_case(
            extraction=extraction,
            case_id=case_id,
            judge_evaluation=judge_evaluation,
            trace=trace,
        )

        timeline_entries = self.build_timeline_entries(
            case_id=case_id,
            timeline_entries=extraction.timeline_entries,
        )

        troubleshooting_actions = self.build_troubleshooting_actions(
            case_id=case_id,
            troubleshooting_actions=extraction.troubleshooting_actions,
        )

        print(
            "[MAPPER] IncidentCaseModel generado:",
            self._summarize_incident_case(incident_case),
        )
        print(
            "[MAPPER] timeline_entries generados:",
            {
                "count": len(timeline_entries),
                "items": [
                    self._summarize_timeline_entry(entry)
                    for entry in timeline_entries
                ],
            },
        )
        print(
            "[MAPPER] troubleshooting_actions generados:",
            {
                "count": len(troubleshooting_actions),
                "items": [
                    self._summarize_troubleshooting_action(action)
                    for action in troubleshooting_actions
                ],
            },
        )

        return CanonicalExtractionPersistenceBundle(
            incident_case=incident_case,
            timeline_entries=timeline_entries,
            troubleshooting_actions=troubleshooting_actions,
        )

    def build_incident_case(
        self,
        *,
        extraction: CanonicalExtractionResult,
        case_id: str,
        judge_evaluation: dict | None = None,
        trace: object | None = None,
    ) -> IncidentCaseModel:
        incident = extraction.incident_case
        metadata = extraction.extraction_metadata

        enrichment_json: dict[str, object] = {
            "extraction_metadata": metadata.model_dump(mode="json"),
        }

        if judge_evaluation is not None:
            enrichment_json["judge_evaluation"] = judge_evaluation

        if trace is not None:
            enrichment_json["agentic_trace"] = trace

        return IncidentCaseModel(
            case_id=case_id,
            source_type=incident.source_type,
            header=self._clean_optional_text(incident.header),
            failure_text=incident.failure_text.strip(),
            impact_text=self._clean_optional_text(incident.impact_text),
            start_time=parse_incident_datetime(incident.start_time),
            solution_time=parse_incident_datetime(incident.solution_time),
            status=incident.incident_status.strip(),
            pending_rca=incident.pending_rca,
            raw_sms=incident.raw_sms.strip(),
            probable_cause_text=self._clean_optional_text(incident.probable_cause_text),
            resolution_summary=self._clean_optional_text(incident.resolution_summary),
            component_types=self._clean_string_list(incident.component_types),
            components_affected=self._clean_string_list(incident.components_affected),
            services_affected=self._clean_string_list(incident.services_affected),
            symptoms=self._clean_string_list(incident.symptoms),
            teams_involved=self._clean_string_list(incident.teams_involved),
            tickets=self._clean_string_list(incident.tickets),
            tags=self._clean_string_list(incident.tags),
            parser_output_json=extraction.model_dump(mode="json"),
            enrichment_json=enrichment_json,
        )

    def build_timeline_entries(
        self,
        *,
        case_id: str,
        timeline_entries: list[CanonicalTimelineEntryData],
    ) -> list[IncidentTimelineEntryModel]:
        entries: list[IncidentTimelineEntryModel] = []

        for item in sorted(timeline_entries, key=lambda x: x.sequence_order):
            entries.append(
                IncidentTimelineEntryModel(
                    case_id=case_id,
                    event_time=self._clean_optional_text(item.event_time),
                    event_text=item.event_text.strip(),
                    event_type=self._clean_optional_text(item.event_type),
                    team=self._clean_optional_text(item.team),
                    action_detected=self._clean_optional_text(item.action_detected),
                    observation_detected=self._clean_optional_text(item.observation_detected),
                    sequence_order=item.sequence_order,
                )
            )

        return entries

    def build_troubleshooting_actions(
        self,
        *,
        case_id: str,
        troubleshooting_actions: list[CanonicalTroubleshootingActionData],
    ) -> list[TroubleshootingActionModel]:
        actions: list[TroubleshootingActionModel] = []

        for item in sorted(troubleshooting_actions, key=lambda x: x.sequence_order):
            actions.append(
                TroubleshootingActionModel(
                    case_id=case_id,
                    action_text=item.action_text.strip(),
                    action_type=self._clean_optional_text(item.action_type),
                    action_role=self._clean_optional_text(item.action_role),
                    target_component=self._clean_optional_text(item.target_component),
                    outcome=self._clean_optional_text(item.outcome),
                    was_effective=item.was_effective,
                    sequence_order=item.sequence_order,
                )
            )

        return actions

    def _clean_string_list(self, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()

        for value in values:
            normalized = value.strip()
            if not normalized:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            cleaned.append(normalized)

        return cleaned

    def _clean_optional_text(self, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    def _summarize_incident_case(
        self,
        incident_case: IncidentCaseModel,
    ) -> dict[str, object]:
        return {
            "case_id": incident_case.case_id,
            "source_type": incident_case.source_type,
            "status": incident_case.status,
            "header": incident_case.header,
            "start_time": incident_case.start_time.isoformat()
            if incident_case.start_time is not None
            else None,
            "failure_text": incident_case.failure_text[:160],
            "tickets": incident_case.tickets,
        }

    def _summarize_timeline_entry(
        self,
        entry: IncidentTimelineEntryModel,
    ) -> dict[str, object]:
        return {
            "sequence_order": entry.sequence_order,
            "event_time": entry.event_time,
            "event_type": entry.event_type,
            "team": entry.team,
            "event_text": entry.event_text[:160],
        }

    def _summarize_troubleshooting_action(
        self,
        action: TroubleshootingActionModel,
    ) -> dict[str, object]:
        return {
            "sequence_order": action.sequence_order,
            "action_type": action.action_type,
            "action_role": action.action_role,
            "target_component": action.target_component,
            "action_text": action.action_text[:160],
        }
