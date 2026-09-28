import importlib.util
import json
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


if __name__ == "__main__":
    unittest.main()
