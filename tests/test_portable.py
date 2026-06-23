import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from speech_app.portable import build_portable_env, portable_data_dir


class PortableModeTests(unittest.TestCase):
    def test_data_dir_prefers_explicit_speech_data_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"

            with patch.dict(os.environ, {"SPEECH_DATA_DIR": str(data_dir)}):
                self.assertEqual(portable_data_dir(), data_dir)

    def test_build_portable_env_keeps_models_and_data_under_root(self):
        root = Path("D:/Speech")

        env = build_portable_env(root)

        self.assertEqual(env["SPEECH_HOME"], str(root))
        self.assertEqual(env["SPEECH_DATA_DIR"], str(root / "data"))
        self.assertEqual(env["HF_HOME"], str(root / "models" / "huggingface"))
        self.assertEqual(env["HF_HUB_CACHE"], str(root / "models" / "huggingface" / "hub"))
        self.assertEqual(env["TORCH_HOME"], str(root / "models" / "torch"))


if __name__ == "__main__":
    unittest.main()
