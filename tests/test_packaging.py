from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_bootstrap_defaults_to_public_repository(self):
        bootstrap = (ROOT / "bootstrap.ps1").read_text(encoding="utf-8")
        shell_bootstrap = (ROOT / "bootstrap.sh").read_text(encoding="utf-8")

        self.assertIn('TheRofli/speech', bootstrap)
        self.assertIn("TheRofli/speech", shell_bootstrap)

    def test_readme_contains_one_line_install_command(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("raw.githubusercontent.com/TheRofli/speech/main/bootstrap.ps1", readme)
        self.assertIn("raw.githubusercontent.com/TheRofli/speech/main/bootstrap.sh", readme)
        self.assertIn("speech parakeet install", readme)

    def test_readme_is_not_tied_to_one_local_machine(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertNotIn("80 GB", readme)
        self.assertNotIn("D:\\Speech", readme)
        self.assertIn("Windows 11 or macOS", readme)

    def test_macos_launcher_files_are_present(self):
        for path in [
            ROOT / "bootstrap.sh",
            ROOT / "install.sh",
            ROOT / "speech.sh",
            ROOT / "bin" / "speech",
        ]:
            self.assertTrue(path.exists(), f"Missing {path}")

    def test_gitignore_excludes_heavy_local_artifacts(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

        for entry in [
            ".venv/",
            "models/",
            "data/",
            "tauri/node_modules/",
            "tauri/src-tauri/target/",
        ]:
            self.assertIn(entry, gitignore)


if __name__ == "__main__":
    unittest.main()
