import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from speech_app.model_status import ModelStatus, find_model_status
from speech_app.parakeet_engine import EngineUnavailable, LoadedEngine, ParakeetEngine
from speech_app.settings import AppSettings


class ModelStatusTests(unittest.TestCase):
    def test_reports_missing_model_when_snapshot_dir_is_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            status = find_model_status(Path(tmp), "nvidia/parakeet-tdt-0.6b-v3")

        self.assertFalse(status.installed)
        self.assertEqual(status.label, "Not installed")

    def test_reports_installed_model_and_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = (
                root
                / "hub"
                / "models--nvidia--parakeet-tdt-0.6b-v3"
                / "snapshots"
                / "abc"
            )
            snapshot.mkdir(parents=True)
            (snapshot / "weights.bin").write_bytes(b"x" * 1024)

            status = find_model_status(root, "nvidia/parakeet-tdt-0.6b-v3")

        self.assertTrue(status.installed)
        self.assertEqual(status.snapshot, "abc")
        self.assertEqual(status.size_mb, 0.001)
        self.assertIn("Installed", status.label)

    def test_ignores_newer_incomplete_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshots = (
                root
                / "hub"
                / "models--nvidia--parakeet-tdt-0.6b-v3"
                / "snapshots"
            )
            complete = snapshots / "complete"
            incomplete = snapshots / "incomplete"
            complete.mkdir(parents=True)
            incomplete.mkdir(parents=True)
            (complete / "model.safetensors").write_bytes(b"weights")
            (incomplete / "config.json").write_text("{}", encoding="utf-8")
            os.utime(complete, (1, 1))
            os.utime(incomplete, (2, 2))

            status = find_model_status(root, "nvidia/parakeet-tdt-0.6b-v3")

        self.assertTrue(status.installed)
        self.assertEqual(status.snapshot, "complete")

    def test_engine_loads_from_complete_local_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = (
                root
                / "hub"
                / "models--nvidia--parakeet-tdt-0.6b-v3"
                / "snapshots"
                / "complete"
            )
            snapshot.mkdir(parents=True)
            (snapshot / "model.safetensors").write_bytes(b"weights")
            engine = ParakeetEngine()
            loaded = LoadedEngine("transformers", "cpu", "model", object())
            engine._load_transformers = Mock(return_value=loaded)

            with patch.dict(os.environ, {"HF_HOME": str(root)}):
                result = engine.load(AppSettings(backend="auto", device="cpu"))

        self.assertIs(result, loaded)
        engine._load_transformers.assert_called_once_with(
            "nvidia/parakeet-tdt-0.6b-v3", "cpu", snapshot
        )

    def test_engine_refuses_to_download_missing_model_during_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = ParakeetEngine()
            engine._load_transformers = Mock()

            with patch.dict(os.environ, {"HF_HOME": tmp}):
                with self.assertRaisesRegex(EngineUnavailable, "parakeet install"):
                    engine.load(AppSettings(backend="transformers", device="cpu"))

        engine._load_transformers.assert_not_called()

    def test_resource_status_formats_memory_and_cpu(self):
        status = ModelStatus(
            installed=True,
            snapshot="abc",
            path=Path("D:/Speech/model"),
            size_mb=1536.0,
        )

        self.assertEqual(status.size_label, "1.50 GB")


if __name__ == "__main__":
    unittest.main()
