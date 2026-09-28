import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gantt.py"
SPEC = importlib.util.spec_from_file_location("eetm_gantt", SCRIPT)
gantt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gantt)


class GanttSyncTest(unittest.TestCase):
    def test_manual_due_and_status_survive_later_agent_sync(self):
        data = gantt.empty()
        gantt.apply_action(data, {"action": "create_chart", "name": "Research"})
        chart = data["charts"][0]
        gantt.apply_action(data, {"action": "create_project", "chart_id": chart["id"], "name": "Study", "workspace": "/research/study"})
        event = {"workspace": "/research/study", "key": "pilot", "title": "Run pilot", "status": "active", "due": "2026-10-02", "workrefs": ["codex/session/1"], "observed_at": "2026-09-28T10:00:00+08:00"}
        self.assertEqual(gantt.sync(data, {"events": [event]})["created"], 1)
        task = chart["tasks"][0]
        gantt.apply_action(data, {"action": "update_task", "chart_id": chart["id"], "task_id": task["id"], "title": task["title"], "start": "", "due": "2026-10-04", "status": "active", "progress": 0, "notes": ""})
        event.update(status="done", due="2026-10-03", observed_at="2026-09-29T10:00:00+08:00", workrefs=["codex/session/2"])
        gantt.sync(data, {"events": [event]})
        self.assertEqual(task["due"], "2026-10-04")
        self.assertEqual(task["status"], "done")
        self.assertEqual(len(chart["tasks"]), 1)
        self.assertEqual(task["workrefs"], ["codex/session/1", "codex/session/2"])

    def test_deleted_agent_task_does_not_reappear(self):
        data = gantt.empty()
        gantt.apply_action(data, {"action": "create_chart", "name": "Research"})
        chart = data["charts"][0]
        gantt.apply_action(data, {"action": "create_project", "chart_id": chart["id"], "name": "Study", "workspace": "/research/study"})
        event = {"workspace": "/research/study", "key": "pilot", "title": "Run pilot", "workrefs": ["codex/session/1"]}
        gantt.sync(data, {"events": [event]})
        gantt.apply_action(data, {"action": "delete_task", "chart_id": chart["id"], "task_id": chart["tasks"][0]["id"]})
        result = gantt.sync(data, {"events": [event]})
        self.assertEqual(result["skipped"], 1)
        self.assertFalse(chart["tasks"])

    def test_data_write_is_private_and_persistent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "board.json"
            data = gantt.empty()
            gantt.write(path, data)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(gantt.read(path)["version"], 1)


if __name__ == "__main__":
    unittest.main()
