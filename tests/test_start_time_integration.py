import unittest
from datetime import UTC, datetime
from unittest.mock import Mock
from zoneinfo import ZoneInfo

from app.agentic.contracts.canonical_extraction import (
    CanonicalExtractionMetadata,
    CanonicalExtractionResult,
    CanonicalIncidentCaseData,
)
from app.api.schemas.incident_requests import IngestSmsRequest
from app.parsers.sms_bitacora_parser import SmsBitacoraParser
from app.services.canonical_extraction_persistence_service import (
    CanonicalExtractionPersistenceService,
)
from app.services.mappers.canonical_extraction_mapper import CanonicalExtractionMapper


LIMA_TZ = ZoneInfo("America/Lima")


def build_extraction(
    *,
    start_time: str | None,
    solution_time: str | None = None,
) -> CanonicalExtractionResult:
    return CanonicalExtractionResult(
        incident_case=CanonicalIncidentCaseData(
            case_id="INC000000123456",
            source_type="sms_bitacora",
            header="HEADER",
            failure_text="FAILURE",
            impact_text="IMPACT",
            start_time=start_time,
            solution_time=solution_time,
            incident_status="closed",
            raw_sms=(
                "INC000000123456\n"
                "FECHA/H.Inicio: 13/03/2026 7:16 hrs.\n"
                "FECHA/H.Fin: 13/03/2026 8:13 hrs."
            ),
            tickets=["INC000000123456"],
        ),
        extraction_metadata=CanonicalExtractionMetadata(
            extractor_name="test",
            extractor_version="v1",
        ),
    )


class StartTimeIntegrationTests(unittest.TestCase):
    def test_sms_parser_extracts_explicit_start_time(self) -> None:
        parser = SmsBitacoraParser()
        payload = IngestSmsRequest(
            raw_text=(
                "INC000000123456\n"
                "FALLA: Portal no disponible\n"
                "FECHA/H.Inicio: 13/03/2026 7:16 hrs.\n"
                "FECHA/H.Fin: 13/03/2026 8:13 hrs."
            ),
            source_channel="sms",
            received_at=datetime(2026, 3, 13, 8, 30, tzinfo=UTC),
        )

        parsed = parser.parse(payload)

        self.assertEqual(
            parsed.start_time,
            datetime(2026, 3, 13, 7, 16, tzinfo=LIMA_TZ),
        )

    def test_mapper_converts_explicit_start_time_to_orm_datetime(self) -> None:
        mapper = CanonicalExtractionMapper()

        bundle = mapper.to_persistence_bundle(
            extraction=build_extraction(start_time="13/03/2026 7:16 hrs."),
            case_id="INC000000123456",
        )

        self.assertEqual(
            bundle.incident_case.start_time,
            datetime(2026, 3, 13, 7, 16, tzinfo=LIMA_TZ),
        )

    def test_mapper_converts_explicit_solution_time_to_orm_datetime(self) -> None:
        mapper = CanonicalExtractionMapper()

        bundle = mapper.to_persistence_bundle(
            extraction=build_extraction(
                start_time="13/03/2026 7:16 hrs.",
                solution_time="13/03/2026 8:13 hrs.",
            ),
            case_id="INC000000123456",
        )

        self.assertEqual(
            bundle.incident_case.solution_time,
            datetime(2026, 3, 13, 8, 13, tzinfo=LIMA_TZ),
        )

    def test_save_accepted_result_persists_start_time(self) -> None:
        db = Mock()
        service = CanonicalExtractionPersistenceService(db_session=db)
        extraction = build_extraction(
            start_time="13/03/2026 7:16 hrs.",
            solution_time="13/03/2026 8:13 hrs.",
        )

        result = service.save_accepted_result(
            extraction=extraction,
            judge_decision="accepted",
        )

        persisted_incident = db.add.call_args_list[0].args[0]

        self.assertEqual(result.case_id, "INC000000123456")
        self.assertEqual(
            persisted_incident.start_time,
            datetime(2026, 3, 13, 7, 16, tzinfo=LIMA_TZ),
        )
        self.assertEqual(
            persisted_incident.solution_time,
            datetime(2026, 3, 13, 8, 13, tzinfo=LIMA_TZ),
        )
        self.assertEqual(
            persisted_incident.parser_output_json["incident_case"]["start_time"],
            "13/03/2026 7:16 hrs.",
        )
        self.assertEqual(
            persisted_incident.parser_output_json["incident_case"]["solution_time"],
            "13/03/2026 8:13 hrs.",
        )
        db.commit.assert_called_once()
        db.rollback.assert_not_called()

    def test_sms_datetime_is_not_shifted_by_utc_conversion(self) -> None:
        mapper = CanonicalExtractionMapper()

        bundle = mapper.to_persistence_bundle(
            extraction=build_extraction(
                start_time="13/03/2026 7:16 hrs.",
                solution_time="13/03/2026 8:13 hrs.",
            ),
            case_id="INC000000123456",
        )

        self.assertEqual(
            bundle.incident_case.start_time.isoformat(),
            "2026-03-13T07:16:00-05:00",
        )
        self.assertEqual(
            bundle.incident_case.solution_time.isoformat(),
            "2026-03-13T08:13:00-05:00",
        )


if __name__ == "__main__":
    unittest.main()
