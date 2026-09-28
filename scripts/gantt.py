#!/usr/bin/env python3
"""Local Gantt board and evidence-based sync for explain-everything-to-me."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ASSETS = Path(__file__).resolve().parents[1] / "gantt"
DEFAULT_DATA = Path.home() / ".explain-everything-to-me" / "gantt" / "data.json"
STATUSES = {"planned", "active", "blocked", "done"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ident() -> str:
    return uuid.uuid4().hex[:12]


def value(text, limit=500):
    if not isinstance(text, str) or len(text) > limit:
        raise ValueError("Invalid text field")
    return text.strip()


def date_value(item):
    if item in (None, ""):
        return None
    if not isinstance(item, str) or not DATE.fullmatch(item):
        raise ValueError("Date must be YYYY-MM-DD")
    datetime.strptime(item, "%Y-%m-%d")
    return item


def empty():
    return {"version": 1, "updated_at": now(), "last_sync_at": None, "charts": []}


def read(path: Path):
    if not path.exists():
        return empty()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("charts"), list):
        raise ValueError("Unsupported Gantt data version")
    return data


def write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = now()
    fd, temp = tempfile.mkstemp(prefix=".gantt-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


@contextlib.contextmanager
def locked(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    with open(lock_path, "a+") as handle:
        os.chmod(lock_path, 0o600)
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def find_chart(data, chart_id):
    return next((x for x in data["charts"] if x["id"] == chart_id), None)


def find_project(chart, project_id):
    return next((x for x in chart["projects"] if x["id"] == project_id), None)


def clean_task_fields(payload):
    status = payload.get("status", "planned")
    if status not in STATUSES:
        raise ValueError("Invalid task status")
    progress = int(payload.get("progress", 0))
    if not 0 <= progress <= 100:
        raise ValueError("Progress must be 0–100")
    start, due = date_value(payload.get("start")), date_value(payload.get("due"))
    if start and due and start > due:
        raise ValueError("Start cannot follow due date")
    return {
        "title": value(payload.get("title", ""), 160),
        "start": start,
        "due": due,
        "status": status,
        "progress": progress,
        "notes": value(payload.get("notes", ""), 5000),
    }


def apply_action(data, payload):
    action = payload.get("action")
    chart = find_chart(data, payload.get("chart_id"))
    if action == "create_chart":
        data["charts"].append({"id": ident(), "name": value(payload.get("name", ""), 100) or "新甘特图", "description": value(payload.get("description", ""), 500), "auto_sync": bool(payload.get("auto_sync", True)), "projects": [], "tasks": [], "deleted_sync_keys": []})
        return
    if chart is None:
        raise ValueError("Chart not found")
    if action == "update_chart":
        chart.update(name=value(payload.get("name", chart["name"]), 100) or chart["name"], description=value(payload.get("description", chart.get("description", "")), 500), auto_sync=bool(payload.get("auto_sync", chart.get("auto_sync", True))))
    elif action == "delete_chart":
        data["charts"].remove(chart)
    elif action == "create_project":
        chart["projects"].append({"id": ident(), "name": value(payload.get("name", ""), 120) or "新项目", "workspace": value(payload.get("workspace", ""), 1000), "deadline_date": date_value(payload.get("deadline_date")), "deadline_label": value(payload.get("deadline_label", ""), 120), "deadline_url": value(payload.get("deadline_url", ""), 1000), "deadline_zone": value(payload.get("deadline_zone", ""), 60)})
    elif action in {"update_project", "delete_project"}:
        project = find_project(chart, payload.get("project_id"))
        if project is None:
            raise ValueError("Project not found")
        if action == "delete_project":
            chart["projects"].remove(project)
            chart["tasks"] = [x for x in chart["tasks"] if x["project_id"] != project["id"]]
        else:
            project.update(name=value(payload.get("name", project["name"]), 120) or project["name"], workspace=value(payload.get("workspace", project.get("workspace", "")), 1000), deadline_date=date_value(payload.get("deadline_date")), deadline_label=value(payload.get("deadline_label", ""), 120), deadline_url=value(payload.get("deadline_url", ""), 1000), deadline_zone=value(payload.get("deadline_zone", ""), 60))
    elif action == "create_task":
        if not find_project(chart, payload.get("project_id")):
            raise ValueError("Project not found")
        fields = clean_task_fields(payload)
        if not fields["title"]:
            raise ValueError("Task title is required")
        chart["tasks"].append({"id": ident(), "project_id": payload["project_id"], "sync_key": None, "source": "manual", "manual_fields": list(fields), "workrefs": [], "evidence_at": None, "updated_at": now(), **fields})
    elif action in {"update_task", "delete_task"}:
        task = next((x for x in chart["tasks"] if x["id"] == payload.get("task_id")), None)
        if task is None:
            raise ValueError("Task not found")
        if action == "delete_task":
            if task.get("sync_key"):
                chart.setdefault("deleted_sync_keys", []).append(task["sync_key"])
            chart["tasks"].remove(task)
        else:
            fields = clean_task_fields(payload)
            if not fields["title"]:
                raise ValueError("Task title is required")
            changed = {field for field, new_value in fields.items() if task.get(field) != new_value}
            task.update(fields)
            task["manual_fields"] = sorted(set(task.get("manual_fields", [])) | changed)
            task["updated_at"] = now()
    else:
        raise ValueError("Unknown action")


def sync(data, payload):
    events = payload.get("events", [])
    if not isinstance(events, list) or len(events) > 100:
        raise ValueError("events must be a list of at most 100 items")
    summary = {"created": 0, "updated": 0, "skipped": 0, "unmapped": []}
    for event in events:
        workspace = value(event.get("workspace", ""), 1000)
        key = value(event.get("key", ""), 180)
        refs = event.get("workrefs", [])
        if not workspace or not key or not isinstance(refs, list) or not refs or any(not isinstance(x, str) or len(x) > 120 for x in refs):
            raise ValueError("Each sync event needs workspace, key, and WorkRef evidence")
        observed = value(event.get("observed_at", ""), 50) or now()
        try:
            observed_dt = datetime.fromisoformat(observed)
        except ValueError as exc:
            raise ValueError("observed_at must be an ISO timestamp with timezone") from exc
        if observed_dt.tzinfo is None:
            raise ValueError("observed_at must have a timezone")
        fields = clean_task_fields(event)
        if not fields["title"]:
            raise ValueError("Task title is required")
        matched = False
        for chart in data["charts"]:
            if not chart.get("auto_sync", True) or (event.get("chart_id") and event["chart_id"] != chart["id"]):
                continue
            for project in chart["projects"]:
                if project.get("workspace") != workspace:
                    continue
                matched = True
                if key in chart.get("deleted_sync_keys", []):
                    summary["skipped"] += 1
                    continue
                task = next((x for x in chart["tasks"] if x["project_id"] == project["id"] and x.get("sync_key") == key), None)
                if task is None:
                    chart["tasks"].append({"id": ident(), "project_id": project["id"], "sync_key": key, "source": "agent", "manual_fields": [], "workrefs": refs[:12], "evidence_at": observed, "updated_at": now(), **fields})
                    summary["created"] += 1
                elif not task.get("evidence_at") or observed_dt >= datetime.fromisoformat(task["evidence_at"]):
                    for field, new_value in fields.items():
                        if field in event and field not in task.get("manual_fields", []):
                            task[field] = new_value
                    task["workrefs"] = list(dict.fromkeys(task.get("workrefs", []) + refs))[-12:]
                    task["evidence_at"] = observed
                    task["updated_at"] = now()
                    summary["updated"] += 1
                else:
                    summary["skipped"] += 1
        if not matched:
            summary["unmapped"].append(workspace)
    data["last_sync_at"] = now()
    return summary


def make_handler(path):
    class Handler(BaseHTTPRequestHandler):
        def _local_host(self):
            host = self.headers.get("Host", "")
            return host.startswith("127.0.0.1:") or host.startswith("localhost:")

        def _json(self, code, content):
            raw = json.dumps(content, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if not self._local_host():
                self._json(403, {"error": "Local host required"})
                return
            route = urlsplit(self.path).path
            if route == "/api/data":
                with locked(path):
                    self._json(200, read(path))
                return
            asset = {"/": "index.html", "/app.js": "app.js", "/styles.css": "styles.css"}.get(route)
            if asset is None:
                self.send_error(404)
                return
            raw = (ASSETS / asset).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", {"index.html": "text/html", "app.js": "text/javascript", "styles.css": "text/css"}[asset] + "; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            if not self._local_host():
                self._json(403, {"error": "Local host required"})
                return
            if urlsplit(self.path).path != "/api/action":
                self.send_error(404)
                return
            origin = self.headers.get("Origin", "")
            expected = f"http://{self.headers.get('Host', '')}"
            if origin and origin != expected:
                self._json(403, {"error": "Foreign origin"})
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self._json(415, {"error": "JSON required"})
                return
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 100_000:
                self._json(413, {"error": "Invalid request size"})
                return
            try:
                payload = json.loads(self.rfile.read(size))
                with locked(path):
                    data = read(path)
                    apply_action(data, payload)
                    write(path, data)
                self._json(200, data)
            except (ValueError, KeyError, TypeError) as exc:
                self._json(400, {"error": str(exc)})

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    sub = parser.add_subparsers(dest="command", required=True)
    server = sub.add_parser("serve", help="Serve the local interactive board")
    server.add_argument("--port", type=int, default=8765)
    sub.add_parser("show", help="Print current chart data")
    sync_parser = sub.add_parser("sync", help="Merge verified agent events from JSON")
    sync_parser.add_argument("--input", required=True, help="JSON file, or - for stdin")
    seed_parser = sub.add_parser("seed", help="Initialize an empty board from JSON")
    seed_parser.add_argument("--input", required=True)
    args = parser.parse_args()
    path = args.data.expanduser().resolve()
    if args.command == "serve":
        with locked(path):
            if not path.exists():
                write(path, empty())
        httpd = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(path))
        print(f"Gantt board: http://127.0.0.1:{httpd.server_port}/", flush=True)
        httpd.serve_forever()
    elif args.command == "show":
        with locked(path):
            print(json.dumps(read(path), ensure_ascii=False, indent=2))
    elif args.command == "seed":
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        if not isinstance(payload.get("charts"), list):
            raise SystemExit("Seed needs charts list")
        with locked(path):
            current = read(path)
            if current["charts"]:
                raise SystemExit("Board already has charts; seed will not replace them")
            payload.setdefault("version", 1)
            payload.setdefault("last_sync_at", None)
            write(path, payload)
        print(f"Seeded {len(payload['charts'])} chart(s): {path}")
    elif args.command == "sync":
        raw = os.sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        payload = json.loads(raw)
        with locked(path):
            data = read(path)
            result = sync(data, payload)
            write(path, data)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
