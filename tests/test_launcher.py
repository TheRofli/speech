from pathlib import Path
import unittest


class LauncherTests(unittest.TestCase):
    def test_powershell_launcher_adds_project_root_to_pythonpath(self):
        script = (Path(__file__).resolve().parents[1] / "speech.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("PYTHONPATH", script)
        self.assertIn("Set-Location -LiteralPath $Root", script)

    def test_default_launcher_starts_app_detached(self):
        script = (Path(__file__).resolve().parents[1] / "speech.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("function Start-SpeechDetached", script)
        self.assertIn("Start-Process", script)
        self.assertIn('Invoke-SpeechPython @("run")', script)
        self.assertIn('Start-SpeechDetached', script.split("if ($SpeechArgs.Count -eq 0)", 1)[1])
        self.assertIn('"foreground"', script)

    def test_launcher_has_stop_and_restart_commands(self):
        script = (Path(__file__).resolve().parents[1] / "speech.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("function Stop-SpeechProcesses", script)
        self.assertIn('"stop"', script)
        self.assertIn('"restart"', script)


if __name__ == "__main__":
    unittest.main()
