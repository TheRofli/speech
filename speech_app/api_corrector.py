from __future__ import annotations

import json
from urllib.request import Request, urlopen

from .secrets import SecretStore
from .settings import AppSettings


class ApiCorrector:
    def __init__(self, secret_store=None, opener=None) -> None:
        self.secret_store = secret_store or SecretStore()
        self.opener = opener or urlopen

    def correct(self, text: str, settings: AppSettings) -> str:
        api_key = self.secret_store.get_api_key()
        if not api_key:
            raise RuntimeError("API key is not configured")
        if not settings.ai_api_model.strip():
            raise RuntimeError("API model is not configured")

        endpoint = settings.ai_api_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": settings.ai_api_model.strip(),
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Correct spelling, punctuation, casing, and obvious speech-to-text "
                        "errors. Preserve meaning, names, numbers, URLs, commands, and the "
                        "speaker's tone. Return only the corrected text."
                    ),
                },
                {"role": "user", "content": text},
            ],
        }
        request = Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with self.opener(request, timeout=settings.ai_timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("API returned an invalid response") from exc
        return str(content).strip()

    def unload(self) -> None:
        return None
