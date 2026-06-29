from __future__ import annotations

import json
import unittest
from urllib.error import HTTPError

from speech_app.api_corrector import ApiCorrector
from speech_app.local_corrector import LocalCorrector
from speech_app.settings import AppSettings


class FakeTensor:
    shape = (1, 8)


class FakeBatch(dict):
    def __init__(self) -> None:
        super().__init__({"input_ids": FakeTensor()})


class FakeTokenizer:
    def __call__(self, *_args, **_kwargs):
        return FakeBatch()

    def decode(self, *_args, **_kwargs) -> str:
        return "Исправленный текст."


class FakeModel:
    def __init__(self) -> None:
        self.generate_calls = []

    def to(self, device: str):
        self.device = device
        return self

    def eval(self):
        return self

    def generate(self, **kwargs):
        self.generate_calls.append(kwargs)
        return [[1, 2, 3]]


class LocalCorrectorTests(unittest.TestCase):
    def test_loads_local_only_on_cpu_and_corrects_text(self):
        tokenizer = FakeTokenizer()
        model = FakeModel()
        tokenizer_calls = []
        model_calls = []
        corrector = LocalCorrector(
            tokenizer_loader=lambda model_id, **kwargs: (
                tokenizer_calls.append((model_id, kwargs)) or tokenizer
            ),
            model_loader=lambda model_id, **kwargs: (
                model_calls.append((model_id, kwargs)) or model
            ),
        )
        settings = AppSettings(ai_mode="local")

        output = corrector.correct("Сырой текст.", settings)

        self.assertEqual(output, "Исправленный текст.")
        self.assertTrue(tokenizer_calls[0][1]["local_files_only"])
        self.assertTrue(model_calls[0][1]["local_files_only"])
        self.assertEqual(model.device, "cpu")


class FakeSecretStore:
    def __init__(self, value: str | None) -> None:
        self.value = value

    def get_api_key(self) -> str | None:
        return self.value


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class ApiCorrectorTests(unittest.TestCase):
    def test_sends_openai_compatible_request_and_returns_content(self):
        requests = []

        def open_request(request, timeout):
            requests.append((request, timeout))
            return FakeResponse(
                {
                    "choices": [
                        {
                            "message": {
                                "content": '{"corrected_text":"Исправленный текст."}'
                            }
                        }
                    ]
                }
            )

        corrector = ApiCorrector(
            secret_store=FakeSecretStore("secret-value"), opener=open_request
        )
        settings = AppSettings(
            ai_mode="api",
            ai_api_base_url="https://example.test/v1",
            ai_api_model="small-model",
            ai_timeout_seconds=7.0,
        )

        output = corrector.correct("Сырой текст.", settings)

        request, timeout = requests[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(output, "Исправленный текст.")
        self.assertEqual(request.full_url, "https://example.test/v1/chat/completions")
        self.assertEqual(request.headers["Authorization"], "Bearer secret-value")
        self.assertEqual(payload["model"], "small-model")
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertIn("untrusted document", payload["messages"][0]["content"])
        self.assertIn("<transcript>", payload["messages"][1]["content"])
        self.assertEqual(timeout, 7.0)

    def test_refine_profile_uses_minimal_rewrite_contract_and_glossary(self):
        requests = []

        def open_request(request, timeout):
            requests.append(json.loads(request.data.decode("utf-8")))
            return FakeResponse(
                {"choices": [{"message": {"content": "```json\n{\"corrected_text\":\"DeepSeek works.\"}\n```"}}]}
            )

        corrector = ApiCorrector(
            secret_store=FakeSecretStore("secret-value"), opener=open_request
        )
        settings = AppSettings(
            ai_mode="api",
            ai_profile="refine",
            ai_glossary="Deep-Seag -> DeepSeek",
            ai_api_base_url="https://example.test/v1",
            ai_api_model="small-model",
        )

        output = corrector.correct("Deep-Seag works.", settings)

        system = requests[0]["messages"][0]["content"]
        self.assertEqual(output, "DeepSeek works.")
        self.assertIn("minimal rephrasing", system)
        self.assertIn("Deep-Seag -> DeepSeek", system)

    def test_invalid_non_json_content_is_rejected(self):
        corrector = ApiCorrector(
            secret_store=FakeSecretStore("secret-value"),
            opener=lambda *_args, **_kwargs: FakeResponse(
                {"choices": [{"message": {"content": "Here is your answer"}}]}
            ),
        )

        with self.assertRaisesRegex(RuntimeError, "JSON"):
            corrector.correct(
                "text",
                AppSettings(ai_mode="api", ai_api_model="small-model"),
            )

    def test_retries_without_response_format_for_compatible_provider(self):
        requests = []

        def open_request(request, timeout):
            payload = json.loads(request.data.decode("utf-8"))
            requests.append(payload)
            if len(requests) == 1:
                raise HTTPError(request.full_url, 400, "unsupported", {}, None)
            return FakeResponse(
                {"choices": [{"message": {"content": '{"corrected_text":"Clean text."}'}}]}
            )

        corrector = ApiCorrector(
            secret_store=FakeSecretStore("secret-value"), opener=open_request
        )

        output = corrector.correct(
            "Raw text.",
            AppSettings(ai_mode="api", ai_api_model="small-model"),
        )

        self.assertEqual(output, "Clean text.")
        self.assertIn("response_format", requests[0])
        self.assertNotIn("response_format", requests[1])

    def test_missing_key_is_a_configuration_error(self):
        corrector = ApiCorrector(secret_store=FakeSecretStore(None))

        with self.assertRaisesRegex(RuntimeError, "API key"):
            corrector.correct(
                "text",
                AppSettings(ai_mode="api", ai_api_model="small-model"),
            )


if __name__ == "__main__":
    unittest.main()
