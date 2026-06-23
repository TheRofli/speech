import tempfile
import unittest
from pathlib import Path

from speech_app.model_status import ModelStatus, find_model_status


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
