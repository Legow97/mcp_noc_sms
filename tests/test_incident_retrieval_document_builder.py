import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.retrieval.incident_retrieval_document_builder import (
    IncidentRetrievalDocumentBuilder,
)
from app.services.retrieval.incident_retrieval_source_reader import (
    IncidentRetrievalCaseData,
    IncidentRetrievalSourceData,
    IncidentRetrievalTimelineEntryData,
    IncidentRetrievalTroubleshootingActionData,
)


LIMA_TZ = ZoneInfo("America/Lima")


class IncidentRetrievalDocumentBuilderTests(unittest.TestCase):
    def test_build_omits_empty_fields_and_renders_sections_in_order(self) -> None:
        builder = IncidentRetrievalDocumentBuilder()
        source_data = IncidentRetrievalSourceData(
            incident_case=IncidentRetrievalCaseData(
                case_id="INC000000123456",
                start_time=datetime(2026, 3, 13, 7, 16, tzinfo=LIMA_TZ),
                header="Portal no disponible",
                failure_text="Falla de autenticacion",
                impact_text="Usuarios sin acceso",
                services_affected=["Portal", "Portal", "API "],
                components_affected=[],
                solution_time=None,
                probable_cause_text=None,
                resolution_summary="Se reinicio el servicio",
                tags=["critical", "portal", "critical"],
            ),
            timeline_entries=[
                IncidentRetrievalTimelineEntryData(
                    event_time=None,
                    event_text="Se valida degradacion",
                    sequence_order=2,
                ),
                IncidentRetrievalTimelineEntryData(
                    event_time="07:16",
                    event_text="Se detecta la falla",
                    sequence_order=1,
                ),
            ],
            troubleshooting_actions=[
                IncidentRetrievalTroubleshootingActionData(
                    sequence_order=2,
                    action_text="Revision de logs",
                    action_type=None,
                ),
                IncidentRetrievalTroubleshootingActionData(
                    sequence_order=1,
                    action_text="Reinicio del servicio",
                    action_type="remediation",
                ),
            ],
        )

        result = builder.build(source_data)

        self.assertEqual(result["case_id"], "INC000000123456")
        self.assertEqual(
            result["document_text"],
            "\n".join(
                [
                    "Case ID: INC000000123456",
                    "Start Time: 2026-03-13T07:16:00-05:00",
                    "Header: Portal no disponible",
                    "Failure: Falla de autenticacion",
                    "Impact: Usuarios sin acceso",
                    "Services Affected: Portal, API",
                    "Timeline:",
                    "- 07:16 - Se detecta la falla",
                    "- Se valida degradacion",
                    "Troubleshooting Actions:",
                    "- 1 - Reinicio del servicio - remediation",
                    "- 2 - Revision de logs",
                    "Resolution Summary: Se reinicio el servicio",
                    "Tags: critical, portal",
                ]
            ),
        )

    def test_build_skips_empty_sections_entirely(self) -> None:
        builder = IncidentRetrievalDocumentBuilder()
        source_data = IncidentRetrievalSourceData(
            incident_case=IncidentRetrievalCaseData(
                case_id="INCEMPTY",
                start_time=None,
                header=None,
                failure_text="Falla",
                impact_text=None,
                services_affected=[],
                components_affected=[],
                solution_time=None,
                probable_cause_text=None,
                resolution_summary=None,
                tags=[],
            ),
            timeline_entries=[],
            troubleshooting_actions=[],
        )

        result = builder.build(source_data)

        self.assertEqual(
            result["document_text"],
            "\n".join(
                [
                    "Case ID: INCEMPTY",
                    "Failure: Falla",
                ]
            ),
        )

    def test_build_keeps_timeline_and_omits_empty_actions_block(self) -> None:
        builder = IncidentRetrievalDocumentBuilder()
        source_data = IncidentRetrievalSourceData(
            incident_case=IncidentRetrievalCaseData(
                case_id="INCTIMELINE",
                start_time=None,
                header=None,
                failure_text="Falla",
                impact_text=None,
                services_affected=[],
                components_affected=[],
                solution_time=None,
                probable_cause_text=None,
                resolution_summary=None,
                tags=[],
            ),
            timeline_entries=[
                IncidentRetrievalTimelineEntryData(
                    event_time="07:16",
                    event_text="Deteccion",
                    sequence_order=1,
                ),
            ],
            troubleshooting_actions=[],
        )

        result = builder.build(source_data)

        self.assertIn("Timeline:\n- 07:16 - Deteccion", result["document_text"])
        self.assertNotIn("Troubleshooting Actions:", result["document_text"])


if __name__ == "__main__":
    unittest.main()
