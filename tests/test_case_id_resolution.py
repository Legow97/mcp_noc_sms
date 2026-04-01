import unittest
from unittest.mock import Mock

from app.agentic.contracts.canonical_extraction import (
    CanonicalExtractionMetadata,
    CanonicalExtractionResult,
    CanonicalIncidentCaseData,
)
from app.services.canonical_extraction_persistence_service import (
    CanonicalExtractionPersistenceService,
)


def build_extraction(
    *,
    case_id: str | None = None,
    tickets: list[str] | None = None,
) -> CanonicalExtractionResult:
    return CanonicalExtractionResult(
        incident_case=CanonicalIncidentCaseData(
            case_id=case_id,
            source_type="sms_bitacora",
            header="HEADER",
            failure_text="FAILURE",
            impact_text="IMPACT",
            incident_status="closed",
            raw_sms="REQ0000000XXX1 TAS0000000XXXX1 INCONVENIENTES",
            tickets=tickets or [],
        ),
        extraction_metadata=CanonicalExtractionMetadata(
            extractor_name="test",
            extractor_version="v1",
        ),
    )


class CaseIdResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.service = CanonicalExtractionPersistenceService(db_session=self.db)

    def test_prefers_agent_case_id_when_valid(self) -> None:
        extraction = build_extraction(
            case_id="tas0000000xxxx1",
            tickets=["REQ0000000XXX1", "INC000000123456"],
        )

        resolved = self.service._resolve_case_id(extraction)

        self.assertEqual(resolved, "TAS0000000XXXX1")

    def test_resolves_from_tickets_using_hierarchy(self) -> None:
        extraction = build_extraction(
            tickets=["CRQ0000000999", "TAS0000000XXXX1", "REQ0000000XXX1"],
        )

        resolved = self.service._resolve_case_id(extraction)

        self.assertEqual(resolved, "REQ0000000XXX1")

    def test_rejects_narrative_words_that_start_with_inc(self) -> None:
        extraction = build_extraction(tickets=["INCONVENIENTES"])

        with self.assertRaisesRegex(ValueError, "No se pudo resolver case_id"):
            self.service._resolve_case_id(extraction)

    def test_does_not_generate_sms_fallback_when_no_valid_ticket_exists(self) -> None:
        extraction = build_extraction(tickets=[])

        with self.assertRaisesRegex(ValueError, "No se pudo resolver case_id"):
            self.service._resolve_case_id(extraction)

    def test_save_accepted_result_persists_with_resolved_ticket_case_id(self) -> None:
        extraction = build_extraction(
            tickets=["REQ0000000XXX1", "TAS0000000XXXX1"],
        )

        result = self.service.save_accepted_result(
            extraction=extraction,
            judge_decision="accepted",
        )

        self.assertEqual(result.case_id, "REQ0000000XXX1")
        self.db.commit.assert_called_once()
        self.db.rollback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
