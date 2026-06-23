import unittest
from unittest.mock import patch

from speech_app.app import build_parser, install_parakeet_model


class CliTests(unittest.TestCase):
    def test_parakeet_install_command_is_available(self):
        args = build_parser().parse_args(["parakeet", "install"])

        self.assertEqual(args.command, "parakeet")
        self.assertEqual(args.parakeet_command, "install")

    def test_diagnose_command_is_available(self):
        args = build_parser().parse_args(["diagnose"])

        self.assertEqual(args.command, "diagnose")

    def test_run_can_open_window_on_start(self):
        args = build_parser().parse_args(["run", "--show-window"])

        self.assertEqual(args.command, "run")
        self.assertTrue(args.show_window)

    def test_parakeet_install_uses_default_model_id(self):
        with patch("builtins.print"), patch(
            "huggingface_hub.snapshot_download", return_value="model-path"
        ) as download:
            exit_code = install_parakeet_model()

        self.assertEqual(exit_code, 0)
        download.assert_called_once_with(repo_id="nvidia/parakeet-tdt-0.6b-v3")


if __name__ == "__main__":
    unittest.main()
