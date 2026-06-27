from __future__ import annotations

import os
import re
import threading
import textwrap
from collections.abc import Callable

from .settings import AppSettings


class LocalCorrector:
    def __init__(
        self,
        tokenizer_loader: Callable | None = None,
        model_loader: Callable | None = None,
    ) -> None:
        self._tokenizer_loader = tokenizer_loader
        self._model_loader = model_loader
        self._tokenizer = None
        self._model = None
        self._model_id = ""
        self._lock = threading.RLock()

    @property
    def is_loaded(self) -> bool:
        return self._model is not None and self._tokenizer is not None

    def load(self, settings: AppSettings) -> None:
        with self._lock:
            if self.is_loaded and self._model_id == settings.ai_local_model_id:
                return
            self.unload()
            tokenizer_loader = self._tokenizer_loader
            model_loader = self._model_loader
            if tokenizer_loader is None or model_loader is None:
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

                tokenizer_loader = AutoTokenizer.from_pretrained
                model_loader = AutoModelForSeq2SeqLM.from_pretrained

            try:
                import torch

                torch.set_num_threads(min(8, max(1, os.cpu_count() or 4)))
            except ImportError:
                pass

            self._tokenizer = tokenizer_loader(
                settings.ai_local_model_id,
                local_files_only=True,
            )
            self._model = model_loader(
                settings.ai_local_model_id,
                local_files_only=True,
            ).to("cpu").eval()
            self._model_id = settings.ai_local_model_id

    def unload(self) -> None:
        with self._lock:
            self._tokenizer = None
            self._model = None
            self._model_id = ""

    def correct(self, text: str, settings: AppSettings) -> str:
        self.load(settings)
        with self._lock:
            chunks = _split_chunks(text, max(80, settings.ai_local_max_chunk_chars))
            return " ".join(self._correct_chunk(chunk) for chunk in chunks).strip()

    def _correct_chunk(self, text: str) -> str:
        inputs = self._tokenizer(
            text,
            padding=False,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        input_length = inputs["input_ids"].shape[1]
        kwargs = {
            **inputs,
            "max_length": min(768, max(16, int(input_length * 1.5))),
            "do_sample": False,
        }
        try:
            import torch

            with torch.inference_mode():
                output = self._model.generate(**kwargs)
        except ImportError:
            output = self._model.generate(**kwargs)
        return self._tokenizer.decode(
            output[0],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        ).strip()


def _split_chunks(text: str, limit: int) -> list[str]:
    text = text.strip()
    if len(text) <= limit:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        parts = textwrap.wrap(
            sentence,
            width=limit,
            break_long_words=False,
            break_on_hyphens=False,
        ) or [sentence]
        for part in parts:
            candidate = f"{current} {part}".strip()
            if current and len(candidate) > limit:
                chunks.append(current)
                current = part
            else:
                current = candidate
    if current:
        chunks.append(current)
    return chunks
