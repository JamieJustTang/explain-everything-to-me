import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ComponentInstallTest(unittest.TestCase):
    def install(self, home, *extra):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "install.py"), "--host", "codex", "--home", str(home), "--no-sivtr", "--no-mcp", *extra],
            capture_output=True, text=True, check=True,
        )

    def test_core_only_and_selected_component(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "core"
            self.install(home, "--no-components")
            bundle = home / ".codex" / "skills" / "explain-everything-to-me"
            self.assertTrue((bundle / "SKILL.md").exists())
            self.assertFalse((bundle / "components").exists())
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "with-gantt"
            self.install(home, "--component", "gantt")
            bundle = home / ".codex" / "skills" / "explain-everything-to-me"
            self.assertTrue((bundle / "components" / "gantt" / "gantt.py").exists())
            self.assertFalse((home / ".explain-everything-to-me" / "gantt" / "data.json").exists())
            sample = bundle / "components" / "gantt" / "example.json"
            target = home / "demo.json"
            subprocess.run([sys.executable, str(bundle / "components" / "gantt" / "gantt.py"), "--data", str(target), "seed", "--input", str(sample)], check=True, capture_output=True)
            data = json.loads(target.read_text())
            self.assertEqual(data["charts"][0]["projects"][0]["workspace"], "/example/workspace/project")
            self.assertFalse(data["charts"][0]["auto_sync"])

    def test_noninteractive_defaults_to_core_and_invalid_component_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "core"
            self.install(home)
            self.assertFalse((home / ".codex" / "skills" / "explain-everything-to-me" / "components").exists())
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "invalid"
            result = subprocess.run([sys.executable, str(ROOT / "scripts" / "install.py"), "--host", "codex", "--home", str(home), "--no-sivtr", "--no-mcp", "--component", "unknown"], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((home / ".codex").exists())

    def test_daily_journal_only_and_multiple_components(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "journal-only"
            result = self.install(home, "--component", "daily-journal")
            bundle = home / ".codex" / "skills" / "explain-everything-to-me"
            self.assertTrue((bundle / "components" / "daily-journal" / "component.json").exists())
            self.assertTrue((bundle / "components" / "daily-journal" / "journal.py").exists())
            self.assertFalse((bundle / "components" / "gantt").exists())
            self.assertFalse((home / ".explain-everything-to-me" / "daily-journal" / "data.json").exists())
            self.assertIn("Daily journal:", result.stdout)
            self.assertNotIn("Optional components were not installed", result.stdout)
            shown = subprocess.run([sys.executable, str(bundle / "components" / "daily-journal" / "journal.py"),
                                    "--data", str(home / "journal.json"), "show"], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(shown.stdout)["entries"], [])
            self.assertFalse((home / "journal.json").exists())
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "both"
            self.install(home, "--component", "gantt", "--component", "daily-journal")
            bundle = home / ".codex" / "skills" / "explain-everything-to-me" / "components"
            self.assertEqual({p.name for p in bundle.iterdir()}, {"gantt", "daily-journal"})

    def test_daily_journal_selected_across_supported_hosts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for host in ("codex", "claude", "dsh", "gemini", "antigravity", "grok", "pi"):
                with self.subTest(host=host):
                    home = root / host
                    args = [sys.executable, str(ROOT / "scripts" / "install.py"), "--host", host,
                            "--home", str(home), "--no-sivtr", "--no-mcp", "--component", "daily-journal"]
                    if host == "antigravity":
                        args.extend(("--workspace", str(home / "workspace")))
                    env = {**os.environ, "DSH_HOME": str(home / ".dsh")}
                    result = subprocess.run(args, capture_output=True, text=True, env=env, check=True)
                    installed = Path(result.stdout.splitlines()[0].split(": ", 1)[1])
                    self.assertTrue((installed / "components" / "daily-journal" / "component.json").exists())
                    self.assertTrue((installed / "references" / "daily-journal-sync.md").exists())


if __name__ == "__main__":
    unittest.main()
