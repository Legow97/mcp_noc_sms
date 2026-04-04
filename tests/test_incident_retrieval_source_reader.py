import unittest
from datetime import datetime
from unittest.mock import Mock
from zoneinfo import ZoneInfo

from app.db.models import (
    IncidentCaseModel,
    IncidentTimelineEntryModel,
    TroubleshootingActionModel,
)
from app.services.retrieval.incident_retrieval_source_reader import (
    IncidentRetrievalSourceReader,
)


LIMA_TZ = ZoneInfo("America/Lima")


class IncidentRetrievalSourceReaderTests(unittest.TestCase):
    def test_read_returns_none_for_unknown_case_id(self) -> None:
        incident_case_repository = Mock()
        incident_case_repository.get_by_case_id.return_value = None

        reader = IncidentRetrievalSourceReader(
            db_session=Mock(),
            incident_case_repository=incident_case_repository,
            timeline_entry_repository=Mock(),
            troubleshooting_action_repository=Mock(),
        )

        result = reader.read("INC404")

        self.assertIsNone(result)
        incident_case_repository.get_by_case_id.assert_called_once_with("INC404")

    def test_read_maps_persisted_entities_without_building_text(self) -> None:
        incident_case = IncidentCaseModel(
            case_id="INC000000123456",
            source_type="sms_bitacora",
            header="Header",
            failure_text="Failure",
            impact_text="Impact",
            start_time=datetime(2026, 3, 13, 7, 16, tzinfo=LIMA_TZ),
            solution_time=datetime(2026, 3, 13, 8, 13, tzinfo=LIMA_TZ),
            status="closed",
            raw_sms="raw text",
            probable_cause_text="Cause",
            resolution_summary="Resolved",
            component_types=[],
            components_affected=["WEB", "DB"],
            services_affected=["Portal"],
            symptoms=[],
            teams_involved=[],
            tickets=[],
            tags=["critical"],
            parser_output_json={},
            enrichment_json={},
        )
        timeline_entries = [
            IncidentTimelineEntryModel(
                case_id="INC000000123456",
                event_time="07:16",
                event_text="Detectada",
                sequence_order=1,
            ),
            IncidentTimelineEntryModel(
                case_id="INC000000123456",
                event_time="07:20",
                event_text="Escalada",
                sequence_order=2,
            ),
        ]
        troubleshooting_actions = [
            TroubleshootingActionModel(
                case_id="INC000000123456",
                action_text="Reinicio",
                action_type="remediation",
                action_role=None,
                target_component=None,
                sequence_order=1,
            ),
        ]

        incident_case_repository = Mock()
        incident_case_repository.get_by_case_id.return_value = incident_case
        timeline_entry_repository = Mock()
        timeline_entry_repository.list_by_case_id.return_value = timeline_entries
        troubleshooting_action_repository = Mock()
        troubleshooting_action_repository.list_by_case_id.return_value = (
            troubleshooting_actions
        )

        reader = IncidentRetrievalSourceReader(
            db_session=Mock(),
            incident_case_repository=incident_case_repository,
            timeline_entry_repository=timeline_entry_repository,
            troubleshooting_action_repository=troubleshooting_action_repository,
        )

        result = reader.read("INC000000123456")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.incident_case.case_id, "INC000000123456")
        self.assertEqual(result.incident_case.services_affected, ["Portal"])
        self.assertEqual(result.incident_case.components_affected, ["WEB", "DB"])
        self.assertEqual(result.incident_case.tags, ["critical"])
        self.assertEqual(
            [entry.sequence_order for entry in result.timeline_entries],
            [1, 2],
        )
        self.assertEqual(
            [entry.event_text for entry in result.timeline_entries],
            ["Detectada", "Escalada"],
        )
        self.assertEqual(
            [action.sequence_order for action in result.troubleshooting_actions],
            [1],
        )
        self.assertEqual(
            result.troubleshooting_actions[0].action_type,
            "remediation",
        )


if __name__ == "__main__":
    unittest.main()
