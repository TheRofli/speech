from __future__ import annotations

import gc
import os
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .model_status import find_model_status
from .settings import AppSettings


class EngineUnavailable(RuntimeError):
    pass


@dataclass(slots=True)
class LoadedEngine:
    backend: str
    device: str
    model_id: str
    model: Any
    processor: Any | None = None


class ParakeetEngine:
    def __init__(self) -> None:
        self.loaded: LoadedEngine | None = None

    @property
    def is_loaded(self) -> bool:
        return self.loaded is not None

    def unload(self) -> None:
        self.loaded = None
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def load(self, settings: AppSettings) -> LoadedEngine:
        backend = settings.backend.lower()
        if backend not in {"auto", "transformers", "nemo"}:
            raise EngineUnavailable(f"Unsupported backend: {settings.backend}")

        device = self._resolve_device(settings.device)
        fallback = Path(__file__).resolve().parents[1] / "models" / "huggingface"
        hf_home = Path(os.environ.get("HF_HOME", str(fallback)))
        status = find_model_status(hf_home, settings.model_id)
        if not status.installed or status.path is None:
            raise EngineUnavailable(
                "Parakeet is not installed locally. Run: speech parakeet install"
            )
        model_path = status.path
        if backend in {"auto", "transformers"}:
            try:
                self.loaded = self._load_transformers(
                    settings.model_id, device, model_path
                )
                return self.loaded
            except EngineUnavailable:
                if backend == "transformers":
                    raise

        self.loaded = self._load_nemo(settings.model_id, device, model_path)
        return self.loaded

    def transcribe(
        self, samples: np.ndarray, sample_rate: int, settings: AppSettings
    ) -> str:
        if samples.size == 0:
            return ""

        loaded = self.loaded
        if (
            loaded is None
            or loaded.model_id != settings.model_id
            or loaded.device != self._resolve_device(settings.device)
            or (settings.backend != "auto" and loaded.backend != settings.backend)
        ):
            loaded = self.load(settings)

        audio = np.asarray(samples, dtype=np.float32).reshape(-1)
        if loaded.backend == "transformers":
            return self._transcribe_transformers(audio, sample_rate, loaded)
        return self._transcribe_nemo(audio, sample_rate, loaded)

    def _resolve_device(self, configured: str) -> str:
        device = configured.lower()
        if device == "auto":
            try:
                import torch

                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        if device in {"gpu", "cuda"}:
            return "cuda"
        return "cpu"

    def _load_transformers(
        self, model_id: str, device: str, model_path: Path
    ) -> LoadedEngine:
        if not any(model_path.glob("*.safetensors")) and not any(
            model_path.glob("*.bin")
        ):
            raise EngineUnavailable(
                "The local snapshot does not contain Transformers weights."
            )
        try:
            import torch
            import transformers
            from transformers import AutoProcessor
        except ImportError as exc:
            raise EngineUnavailable(
                "Transformers backend is not installed. Run install.ps1 or "
                "install requirements-parakeet.txt."
            ) from exc

        AutoModelForTDT = getattr(transformers, "AutoModelForTDT", None)
        if AutoModelForTDT is None:
            raise EngineUnavailable(
                "This Transformers build does not include AutoModelForTDT. "
                "Install Transformers from source as in requirements-parakeet.txt."
            )

        if device == "cuda" and not torch.cuda.is_available():
            raise EngineUnavailable("CUDA was selected, but torch cannot see a GPU.")

        dtype = torch.float32 if device == "cpu" else torch.float16
        try:
            processor = AutoProcessor.from_pretrained(
                str(model_path), local_files_only=True
            )
            try:
                model = AutoModelForTDT.from_pretrained(
                    str(model_path), dtype=dtype, local_files_only=True
                )
            except TypeError:
                model = AutoModelForTDT.from_pretrained(
                    str(model_path),
                    torch_dtype=dtype,
                    local_files_only=True,
                )
        except Exception as exc:
            raise EngineUnavailable(
                "Could not load the local Transformers Parakeet snapshot."
            ) from exc
        model.to(device)
        model.eval()
        return LoadedEngine(
            backend="transformers",
            device=device,
            model_id=model_id,
            model=model,
            processor=processor,
        )

    def _transcribe_transformers(
        self, audio: np.ndarray, sample_rate: int, loaded: LoadedEngine
    ) -> str:
        import torch

        processor = loaded.processor
        model = loaded.model
        inputs = processor(
            [audio],
            sampling_rate=sample_rate,
            return_tensors="pt",
            padding=True,
        )
        if hasattr(inputs, "to"):
            inputs = inputs.to(device=model.device, dtype=model.dtype)
        else:
            inputs = {
                key: value.to(device=model.device)
                if hasattr(value, "to")
                else value
                for key, value in inputs.items()
            }

        with torch.inference_mode():
            output = model.generate(**inputs, return_dict_in_generate=True)

        decoded = processor.decode(output.sequences, skip_special_tokens=True)
        return _normalize_decoded_text(decoded)

    def _load_nemo(
        self, model_id: str, device: str, model_path: Path
    ) -> LoadedEngine:
        nemo_files = sorted(model_path.glob("*.nemo"))
        if not nemo_files:
            raise EngineUnavailable("The local snapshot does not contain NeMo weights.")
        try:
            import nemo.collections.asr as nemo_asr
        except ImportError as exc:
            raise EngineUnavailable(
                "NeMo backend is not installed. On Windows the Transformers "
                "backend is usually the easier route."
            ) from exc

        model = nemo_asr.models.ASRModel.restore_from(
            restore_path=str(nemo_files[0]), map_location=device
        )
        if device == "cuda":
            model = model.cuda()
        else:
            model = model.cpu()
        model.eval()
        return LoadedEngine(
            backend="nemo",
            device=device,
            model_id=model_id,
            model=model,
        )

    def _transcribe_nemo(
        self, audio: np.ndarray, sample_rate: int, loaded: LoadedEngine
    ) -> str:
        wav_path = _write_temp_wav(audio, sample_rate)
        try:
            output = loaded.model.transcribe([str(wav_path)])
        finally:
            try:
                wav_path.unlink()
            except OSError:
                pass
        if not output:
            return ""
        first = output[0]
        return getattr(first, "text", str(first)).strip()


def _normalize_decoded_text(decoded: Any) -> str:
    if isinstance(decoded, str):
        return decoded.strip()
    if isinstance(decoded, tuple) and decoded:
        return _normalize_decoded_text(decoded[0])
    if isinstance(decoded, list):
        return " ".join(str(item).strip() for item in decoded if str(item).strip())
    return str(decoded).strip()


def _write_temp_wav(audio: np.ndarray, sample_rate: int) -> Path:
    clipped = np.clip(audio, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    handle.close()
    path = Path(handle.name)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    return path
