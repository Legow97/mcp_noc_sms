from __future__ import annotations


def build_canonical_extraction_response_schema() -> dict:
    """
    Schema JSON para respuestas compatibles con CanonicalExtractionResult.
    """
    return {
        "type": "OBJECT",
        "properties": {
            "incident_case": {
                "type": "OBJECT",
                "properties": {
                    "source_type": {"type": "STRING"},
                    "header": {"type": "STRING"},
                    "failure_text": {"type": "STRING"},
                    "impact_text": {"type": "STRING"},
                    "incident_status": {"type": "STRING"},
                    "pending_rca": {"type": "BOOLEAN"},
                    "raw_sms": {"type": "STRING"},
                    "probable_cause_text": {"type": "STRING"},
                    "resolution_summary": {"type": "STRING"},
                    "component_types": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "components_affected": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "services_affected": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "symptoms": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "teams_involved": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "tickets": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "tags": {"type": "ARRAY", "items": {"type": "STRING"}},
                },
                "required": [
                    "source_type",
                    "failure_text",
                    "incident_status",
                    "pending_rca",
                    "raw_sms",
                    "component_types",
                    "components_affected",
                    "services_affected",
                    "symptoms",
                    "teams_involved",
                    "tickets",
                    "tags",
                ],
            },
            "timeline_entries": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "event_time": {"type": "STRING"},
                        "event_text": {"type": "STRING"},
                        "event_type": {"type": "STRING"},
                        "team": {"type": "STRING"},
                        "action_detected": {"type": "STRING"},
                        "observation_detected": {"type": "STRING"},
                        "sequence_order": {"type": "INTEGER"},
                    },
                    "required": ["event_text", "sequence_order"],
                },
            },
            "troubleshooting_actions": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "action_text": {"type": "STRING"},
                        "action_type": {"type": "STRING"},
                        "action_role": {"type": "STRING"},
                        "target_component": {"type": "STRING"},
                        "outcome": {"type": "STRING"},
                        "was_effective": {"type": "BOOLEAN"},
                        "sequence_order": {"type": "INTEGER"},
                    },
                    "required": ["action_text", "sequence_order"],
                },
            },
            "extraction_metadata": {
                "type": "OBJECT",
                "properties": {
                    "extractor_name": {"type": "STRING"},
                    "extractor_version": {"type": "STRING"},
                    "model_name": {"type": "STRING"},
                    "confidence_notes": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "warnings": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "missing_fields": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "inferred_fields": {"type": "ARRAY", "items": {"type": "STRING"}},
                },
                "required": [
                    "extractor_name",
                    "extractor_version",
                    "confidence_notes",
                    "warnings",
                    "missing_fields",
                    "inferred_fields",
                ],
            },
        },
        "required": [
            "incident_case",
            "timeline_entries",
            "troubleshooting_actions",
            "extraction_metadata",
        ],
    }


def build_judge_response_schema() -> dict:
    """
    Schema JSON para respuestas compatibles con JudgeDecision.
    """
    return {
        "type": "OBJECT",
        "properties": {
            "decision": {
                "type": "STRING",
                "enum": [
                    "accepted",
                    "accepted_with_observations",
                    "rejected",
                ],
            },
            "score": {"type": "NUMBER"},
            "score_breakdown": {
                "type": "OBJECT",
                "properties": {
                    "fidelity": {"type": "NUMBER"},
                    "coverage": {"type": "NUMBER"},
                    "structural_classification": {"type": "NUMBER"},
                    "semantic_prudence": {"type": "NUMBER"},
                    "metadata_quality": {"type": "NUMBER"},
                },
                "required": [
                    "fidelity",
                    "coverage",
                    "structural_classification",
                    "semantic_prudence",
                    "metadata_quality",
                ],
            },
            "critical_issues": {"type": "ARRAY", "items": {"type": "STRING"}},
            "strengths": {"type": "ARRAY", "items": {"type": "STRING"}},
            "issues": {"type": "ARRAY", "items": {"type": "STRING"}},
            "improvement_actions": {"type": "ARRAY", "items": {"type": "STRING"}},
            "feedback": {"type": "STRING"},
        },
        "required": [
            "decision",
            "score",
            "score_breakdown",
            "critical_issues",
            "strengths",
            "issues",
            "improvement_actions",
            "feedback",
        ],
    }