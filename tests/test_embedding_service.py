import unittest
from types import SimpleNamespace

from app.services.retrieval.embedding_service import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
    EmbeddingService,
)


class FakeModels:
    def __init__(self, response: object | None = None, exception: Exception | None = None) -> None:
        self._response = response
        self._exception = exception
        self.last_config: dict | None = None

    def embed_content(self, *, model: str, contents: str, config: dict) -> object:
        if self._exception is not None:
            raise self._exception
        self.last_config = config
        return self._response


class FakeClient:
    def __init__(self, response: object | None = None, exception: Exception | None = None) -> None:
        self.models = FakeModels(response=response, exception=exception)


class EmbeddingServiceTests(unittest.TestCase):
    def test_embed_text_returns_vector(self) -> None:
        client = FakeClient(
            response=SimpleNamespace(
                embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3])]
            )
        )
        service = EmbeddingService(
            provider_name="gemini",
            model_name="gemini-embedding-001",
            client=client,
        )

        vector = service.embed_text("hola mundo")

        self.assertEqual(vector, [0.1, 0.2, 0.3])
        self.assertEqual(client.models.last_config, {"task_type": "RETRIEVAL_DOCUMENT"})

    def test_embed_text_accepts_custom_task_type(self) -> None:
        client = FakeClient(
            response=SimpleNamespace(
                embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3])]
            )
        )
        service = EmbeddingService(
            provider_name="gemini",
            model_name="gemini-embedding-001",
            client=client,
        )

        vector = service.embed_text("buscar incidentes similares", task_type="RETRIEVAL_QUERY")

        self.assertEqual(vector, [0.1, 0.2, 0.3])
        self.assertEqual(client.models.last_config, {"task_type": "RETRIEVAL_QUERY"})

    def test_embed_text_rejects_empty_input(self) -> None:
        service = EmbeddingService(
            provider_name="gemini",
            model_name="gemini-embedding-001",
            client=FakeClient(),
        )

        with self.assertRaisesRegex(ValueError, "document_text no puede estar vacío"):
            service.embed_text("   ")

    def test_embed_text_raises_provider_error_on_empty_response(self) -> None:
        service = EmbeddingService(
            provider_name="gemini",
            model_name="gemini-embedding-001",
            client=FakeClient(response=SimpleNamespace(embeddings=[])),
        )

        with self.assertRaisesRegex(EmbeddingProviderError, "sin embeddings"):
            service.embed_text("texto real")

    def test_embed_text_raises_provider_error_on_provider_failure(self) -> None:
        service = EmbeddingService(
            provider_name="gemini",
            model_name="gemini-embedding-001",
            client=FakeClient(exception=RuntimeError("provider down")),
        )

        with self.assertRaisesRegex(EmbeddingProviderError, "provider down"):
            service.embed_text("texto real")

    def test_embed_text_raises_configuration_error_without_api_key(self) -> None:
        service = EmbeddingService(
            provider_name="gemini",
            model_name="gemini-embedding-001",
            use_vertexai=False,
            api_key="",
        )

        with self.assertRaisesRegex(EmbeddingConfigurationError, "está vacío"):
            service.embed_text("texto real")

    def test_rejects_unsupported_provider(self) -> None:
        with self.assertRaisesRegex(EmbeddingConfigurationError, "no soportado"):
            EmbeddingService(
                provider_name="openai",
                model_name="any",
                client=FakeClient(),
            )


if __name__ == "__main__":
    unittest.main()
