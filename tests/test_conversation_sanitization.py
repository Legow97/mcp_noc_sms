import unittest

from app.conversation.infrastructure.safety.sanitization import SanitizationService


class ConversationSanitizationTests(unittest.TestCase):
    def test_sanitizes_sensitive_values_with_stable_placeholders(self) -> None:
        service = SanitizationService()
        scope = service.build_scope()
        text = (
            "usuario=jdoe password=supersecret ip=10.1.2.3 "
            "host=api.internal.corp path=/srv/private/config.yml "
            "contacto Juan Perez correo juan.perez@corp.internal"
        )

        sanitized = service.sanitize_text_for_external(text, scope)

        self.assertIn("[SENSITIVE_USER_1]", sanitized)
        self.assertIn("[REDACTED_SECRET_1]", sanitized)
        self.assertIn("[INTERNAL_IP_1]", sanitized)
        self.assertIn("[PRIVATE_DOMAIN_1]", sanitized)
        self.assertIn("[SENSITIVE_PATH_1]", sanitized)
        self.assertIn("[PERSON_1]", sanitized)
        self.assertNotIn("10.1.2.3", sanitized)
        self.assertNotIn("supersecret", sanitized)

    def test_reuses_same_placeholder_within_scope(self) -> None:
        service = SanitizationService()
        scope = service.build_scope()

        first = service.sanitize_text_for_external("password=topsecret", scope)
        second = service.sanitize_text_for_external("password=topsecret", scope)

        self.assertEqual(first, second)
        self.assertIn("[REDACTED_SECRET_1]", first)


if __name__ == "__main__":
    unittest.main()
