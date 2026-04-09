import unittest

from app.core.config import settings
from app.conversation.application.services.clarification_service import (
    ClarificationAssessment,
)
from app.conversation.contracts.requests import ConversationRequest
from app.conversation.contracts.session_models import (
    ConversationContext,
    ConversationSessionState,
)
from app.conversation.infrastructure.research.external_research import (
    ExternalResearchPolicy,
    ExternalResearchPolicyBundle,
    ExternalResearchPolicyLoader,
    ExternalResearchService,
    ExternalResearchSource,
)


class StaticPolicyLoader(ExternalResearchPolicyLoader):
    def __init__(self, bundle: ExternalResearchPolicyBundle) -> None:
        self._bundle = bundle

    def load(self) -> ExternalResearchPolicyBundle:
        return self._bundle


class FakeSearchProvider:
    def __init__(self, sources: list[ExternalResearchSource]) -> None:
        self.sources = sources
        self.last_query: str | None = None

    def search(
        self,
        query: str,
        *,
        max_results: int,
        timeout_seconds: int,
    ) -> list[ExternalResearchSource]:
        self.last_query = query
        return self.sources[:max_results]


class ConversationExternalResearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_flag = settings.features.allow_external_sources
        settings.features.allow_external_sources = True

    def tearDown(self) -> None:
        settings.features.allow_external_sources = self.original_flag

    def test_allows_whitelisted_sources_and_sanitizes_context(self) -> None:
        policy = ExternalResearchPolicy(
            whitelist_domains=["docs.aws.amazon.com"],
            query_domain_hints={"aws": ["docs.aws.amazon.com"]},
            allow_unlisted_domains=False,
        )
        provider = FakeSearchProvider(
            [
                ExternalResearchSource(
                    title="AWS JVM Guidance",
                    url="https://docs.aws.amazon.com/prescriptive-guidance/latest/jvm/memory.html",
                    domain="docs.aws.amazon.com",
                    snippet="Guía oficial sobre memoria y GC.",
                )
            ]
        )
        service = ExternalResearchService(
            policy_loader=StaticPolicyLoader(
                ExternalResearchPolicyBundle(
                    manifest=policy,
                    markdown_policy="# External Research Policy\nUsa fuentes oficiales.",
                )
            ),
            search_provider=provider,
        )

        result = service.research(
            request=ConversationRequest(
                message="Qué recomienda AWS para este patrón de memoria y GC?",
                requested_capabilities=["external_research"],
            ),
            context=ConversationContext(
                session_id="conv-1",
                mode="general",
                latest_user_message="Qué recomienda AWS para este patrón de memoria y GC?",
            ),
            session_state=ConversationSessionState(
                session_id="conv-1",
                active_issue_summary="host api.internal.corp con password=secret123 y 10.2.0.5",
            ),
            clarification=ClarificationAssessment(),
            arguments={},
        )

        self.assertTrue(result.used)
        self.assertEqual(result.sources[0].category, "whitelist")
        self.assertIn("[PRIVATE_DOMAIN_1]", " ".join(result.sanitized_context))
        self.assertIn("[REDACTED_SECRET_1]", " ".join(result.sanitized_context))
        self.assertIn("[INTERNAL_IP_1]", " ".join(result.sanitized_context))
        self.assertIsNotNone(provider.last_query)

    def test_blocks_blacklisted_domain_hints(self) -> None:
        policy = ExternalResearchPolicy(
            blacklist_domains=["reddit.com"],
            query_domain_hints={"reddit": ["reddit.com"]},
        )
        service = ExternalResearchService(
            policy_loader=StaticPolicyLoader(
                ExternalResearchPolicyBundle(
                    manifest=policy,
                    markdown_policy="# External Research Policy\nBloquea blacklists.",
                )
            ),
            search_provider=FakeSearchProvider([]),
        )

        result = service.research(
            request=ConversationRequest(message="Revisa reddit para esta falla"),
            context=ConversationContext(
                session_id="conv-2",
                mode="general",
                latest_user_message="Revisa reddit para esta falla",
            ),
            session_state=ConversationSessionState(session_id="conv-2"),
            clarification=ClarificationAssessment(),
            arguments={},
        )

        self.assertEqual(result.status, "blocked")
        self.assertIn("blacklist", result.blocked_reasons[0].lower())

    def test_uses_caution_mode_for_unlisted_sources(self) -> None:
        policy = ExternalResearchPolicy(
            allow_unlisted_domains=True,
            caution_mode=True,
        )
        service = ExternalResearchService(
            policy_loader=StaticPolicyLoader(
                ExternalResearchPolicyBundle(
                    manifest=policy,
                    markdown_policy="# External Research Policy\nUsa caution mode.",
                )
            ),
            search_provider=FakeSearchProvider(
                [
                    ExternalResearchSource(
                        title="Unlisted Reference",
                        url="https://example.com/docs/gc",
                        domain="example.com",
                        snippet="Referencia genérica.",
                    )
                ]
            ),
        )

        result = service.research(
            request=ConversationRequest(
                message="Consulta fuentes sobre tuning de GC",
                requested_capabilities=["external_research"],
            ),
            context=ConversationContext(
                session_id="conv-3",
                mode="general",
                latest_user_message="Consulta fuentes sobre tuning de GC",
            ),
            session_state=ConversationSessionState(session_id="conv-3"),
            clarification=ClarificationAssessment(),
            arguments={},
        )

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.sources[0].category, "unlisted")
        self.assertEqual(result.policy_mode, "caution")


if __name__ == "__main__":
    unittest.main()
