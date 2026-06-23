from __future__ import annotations

import os
from pathlib import Path


def portable_data_dir() -> Path | None:
    value = os.environ.get("SPEECH_DATA_DIR")
    if not value:
        return None
    return Path(value)


def build_portable_env(root: Path) -> dict[str, str]:
    model_root = root / "models"
    hf_home = model_root / "huggingface"
    return {
        "SPEECH_HOME": str(root),
        "SPEECH_DATA_DIR": str(root / "data"),
        "HF_HOME": str(hf_home),
        "HF_HUB_CACHE": str(hf_home / "hub"),
        "TRANSFORMERS_CACHE": str(hf_home / "transformers"),
        "TORCH_HOME": str(model_root / "torch"),
        "XDG_CACHE_HOME": str(root / "cache"),
    }

