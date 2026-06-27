from __future__ import annotations

import json
import unittest

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
                {"choices": [{"message": {"content": "Исправленный текст."}}]}
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
        self.assertEqual(timeout, 7.0)

    def test_missing_key_is_a_configuration_error(self):
        corrector = ApiCorrector(secret_store=FakeSecretStore(None))

        with self.assertRaisesRegex(RuntimeError, "API key"):
            corrector.correct(
                "text",
                AppSettings(ai_mode="api", ai_api_model="small-model"),
            )


if __name__ == "__main__":
    unittest.main()
