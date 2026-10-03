#!/usr/bin/env python3
"""Local daily journal prototype with event and narrative import interfaces."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import mimetypes
import os
import re
import tempfile
import uuid
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
DEFAULT_DATA = Path.home() / ".explain-everything-to-me" / "daily-journal" / "data.json"
KINDS = {"progress", "artifact", "insight", "share"}
READINESS = {"private", "discussable", "shared"}


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def clean(value, limit=1000):
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError("Invalid text")
    return value.strip()


def day(value):
    if not isinstance(value, str):
        raise ValueError("Date must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError("Date must be YYYY-MM-DD") from exc


def blank():
    return {"version": 1, "entries": [], "digests": {}, "updated_at": timestamp(), "last_import_at": None}


def read(path):
    if not path.exists():
        return blank()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("entries"), list):
        raise ValueError("Unsupported journal data")
    return data


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = timestamp()
    fd, temp = tempfile.mkstemp(prefix=".journal-", dir=path.parent)
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
def locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock")
    with open(lock, "a+") as handle:
        os.chmod(lock, 0o600)
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def fields(payload, *, agent=False):
    kind = payload.get("kind", "progress")
    readiness = payload.get("readiness", "private")
    if kind not in KINDS or readiness not in READINESS:
        raise ValueError("Invalid kind or readiness")
    title = clean(payload.get("title", ""), 140)
    if not title:
        raise ValueError("Title is required")
    refs = payload.get("workrefs", [])
    if not isinstance(refs, list) or len(refs) > 12 or any(not isinstance(ref, str) or not ref or len(ref) > 160 for ref in refs):
        raise ValueError("Invalid WorkRefs")
    if agent and not refs:
        raise ValueError("Agent entries require WorkRef evidence")
    if agent and readiness == "shared":
        raise ValueError("Only the user can mark an entry shared")
    artifact_target = clean(payload.get("artifact_target", ""), 1200)
    if artifact_target and not (artifact_target.startswith("/") or artifact_target.startswith("demo:") or
                                artifact_target.startswith("https://") or artifact_target.startswith("http://")):
        raise ValueError("Artifact target must be an HTTP URL or absolute path")
    return {"date": day(payload.get("date", "")), "kind": kind, "title": title,
            "detail": clean(payload.get("detail", ""), 3000),
            "project": clean(payload.get("project", ""), 140),
            "artifact": clean(payload.get("artifact", ""), 700),
            "artifact_target": artifact_target,
            "readiness": readiness, "workrefs": list(dict.fromkeys(refs))}


def action(data, payload):
    op = payload.get("action")
    if op == "create":
        item = fields(payload)
        data["entries"].append({"id": uuid.uuid4().hex[:12], "source": "manual", "key": None,
                                "manual_fields": list(item), "updated_at": timestamp(), **item})
    elif op in {"update", "delete"}:
        item = next((entry for entry in data["entries"] if entry["id"] == payload.get("id")), None)
        if item is None:
            raise ValueError("Entry not found")
        if op == "delete":
            data["entries"].remove(item)
            if item.get("key"):
                data.setdefault("deleted_keys", []).append(item["key"])
        else:
            changed = fields(payload)
            item["manual_fields"] = sorted(set(item.get("manual_fields", [])) | {key for key, value in changed.items() if item.get(key) != value})
            item.update(changed)
            item["updated_at"] = timestamp()
    else:
        raise ValueError("Unknown action")


def import_events(data, payload):
    events = payload.get("events")
    if not isinstance(events, list) or len(events) > 100:
        raise ValueError("events must be a list of at most 100")
    result = {"created": 0, "updated": 0, "skipped": 0}
    for event in events:
        key = clean(event.get("key", ""), 180)
        if not key:
            raise ValueError("Stable key is required")
        item = fields(event, agent=True)
        if key in data.get("deleted_keys", []):
            result["skipped"] += 1
            continue
        existing = next((entry for entry in data["entries"] if entry.get("key") == key), None)
        if existing:
            previous_refs = existing.get("workrefs", [])
            changed = False
            for field, value in item.items():
                if field == "workrefs":
                    continue
                if field not in existing.get("manual_fields", []) and existing.get(field) != value:
                    existing[field] = value
                    changed = True
            merged_refs = list(dict.fromkeys(previous_refs + item["workrefs"]))[-12:]
            if merged_refs != previous_refs:
                existing["workrefs"] = merged_refs
                changed = True
            if changed:
                existing["updated_at"] = timestamp()
            result["updated"] += 1
        else:
            data["entries"].append({"id": uuid.uuid4().hex[:12], "source": "agent", "key": key,
                                    "manual_fields": [], "updated_at": timestamp(), **item})
            result["created"] += 1
    data["last_import_at"] = timestamp()
    return result



def compose(data, payload):
    report_date = day(payload.get("date", ""))
    todays = {entry["id"]: entry for entry in data["entries"] if entry["date"] == report_date}
    sections = payload.get("sections", [])
    if not isinstance(sections, list) or not 1 <= len(sections) <= 8:
        raise ValueError("Digest needs 1–8 narrative sections")

    def entry_ids(value):
        if not isinstance(value, list) or len(value) > 12 or any(ref not in todays for ref in value):
            raise ValueError("Digest references must point to entries from this date")
        return list(dict.fromkeys(value))

    def require_inline_artifacts(body, refs):
        markers = set(re.findall(r"\[\[artifact:([\w-]+)\]\]", body))
        if any(todays[ref].get("artifact") and ref not in markers for ref in refs):
            raise ValueError("Artifact references must appear inside the prose")

    rendered = []
    referenced = set()
    for section in sections:
        if not isinstance(section, dict):
            raise ValueError("Invalid digest section")
        refs = entry_ids(section.get("entry_ids", []))
        if not refs:
            raise ValueError("Each section needs at least one journal entry")
        body = clean(section.get("body", ""), 4000)
        require_inline_artifacts(body, refs)
        referenced.update(refs)
        rendered.append({"heading": clean(section.get("heading", ""), 140),
                         "body": body, "entry_ids": refs})
        if not rendered[-1]["heading"] or not rendered[-1]["body"]:
            raise ValueError("Digest heading and body are required")
    letter = payload.get("letter")
    if not isinstance(letter, dict):
        raise ValueError("Ready to Share needs a recommendation letter")
    letter_refs = entry_ids(letter.get("entry_ids", []))
    if not any(todays[ref].get("artifact") for ref in letter_refs):
        raise ValueError("Ready to Share must cite at least one artifact")
    letter_body = clean(letter.get("body", ""), 3000)
    require_inline_artifacts(letter_body, letter_refs)
    referenced.update(letter_refs)
    result = {"date": report_date, "title": clean(payload.get("title", ""), 180),
              "lead": clean(payload.get("lead", ""), 1500), "sections": rendered,
              "closing": clean(payload.get("closing", ""), 1500),
              "letter": {"salutation": clean(letter.get("salutation", ""), 120),
                         "body": letter_body,
                         "recipient": clean(letter.get("recipient", ""), 240),
                         "suggested_ask": clean(letter.get("suggested_ask", ""), 700),
                         "entry_ids": letter_refs},
              "entry_versions": {ref: todays[ref]["updated_at"] for ref in referenced},
              "generated_at": timestamp()}
    if not result["title"] or not result["lead"] or not result["letter"]["body"]:
        raise ValueError("Digest title, lead, and recommendation letter are required")
    data.setdefault("digests", {})[report_date] = result
    return result


def artifact_file(entry):
    target = entry.get("artifact_target", "")
    if target.startswith("demo:"):
        name = target[5:]
        if not name or Path(name).name != name:
            return None
        path = (HERE / "example-artifacts" / name).resolve()
        if not path.is_relative_to((HERE / "example-artifacts").resolve()):
            return None
        return path
    if target.startswith("/"):
        return Path(target).resolve()
    return None


def handler_for(path):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, code, payload):
            raw = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def local(self):
            return self.headers.get("Host", "").split(":")[0] in {"127.0.0.1", "localhost"}

        def do_GET(self):
            if not self.local():
                return self.respond(403, {"error": "Local host required"})
            route = urlsplit(self.path).path
            if route == "/api/data":
                with locked(path):
                    return self.respond(200, read(path))
            if route.startswith("/api/artifact/"):
                entry_id = route.removeprefix("/api/artifact/")
                with locked(path):
                    entry = next((item for item in read(path)["entries"] if item["id"] == entry_id), None)
                artifact = artifact_file(entry) if entry else None
                if not artifact or not artifact.is_file() or artifact.stat().st_size > 25_000_000:
                    return self.respond(404, {"error": "Artifact not available"})
                kind = mimetypes.guess_type(artifact.name)[0] or "application/octet-stream"
                if kind not in {"application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml", "text/plain"}:
                    kind = "text/plain" if artifact.suffix.lower() in {".md", ".csv", ".json", ".py", ".js", ".html", ".css"} else "application/octet-stream"
                raw = artifact.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", kind + ("; charset=utf-8" if kind == "text/plain" else ""))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Security-Policy", "default-src 'none'; sandbox")
                self.send_header("Content-Disposition", ("inline" if kind != "application/octet-stream" else "attachment") + f'; filename="{artifact.name.encode("ascii", "ignore").decode() or "artifact"}"')
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                return self.wfile.write(raw)
            file = {"/": "index.html", "/app.js": "app.js", "/styles.css": "styles.css",
                    "/vendor/gsap.min.js": "vendor/gsap.min.js"}.get(route)
            if not file:
                return self.respond(404, {"error": "Not found"})
            raw = (HERE / file).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", {"index.html": "text/html", "app.js": "text/javascript",
                                              "styles.css": "text/css", "vendor/gsap.min.js": "text/javascript"}[file] + "; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            if not self.local() or self.headers.get("Origin", "") not in {"", f"http://{self.headers.get('Host', '')}"}:
                return self.respond(403, {"error": "Local origin required"})
            if urlsplit(self.path).path != "/api/action" or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.respond(404, {"error": "Not found"})
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 100_000:
                return self.respond(413, {"error": "Invalid request size"})
            try:
                payload = json.loads(self.rfile.read(size))
                with locked(path):
                    data = read(path)
                    action(data, payload)
                    write(path, data)
                self.respond(200, data)
            except (ValueError, KeyError, TypeError) as exc:
                self.respond(400, {"error": str(exc)})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8767)
    sub.add_parser("show")
    ingest = sub.add_parser("import")
    ingest.add_argument("--input", required=True)
    digest = sub.add_parser("compose")
    digest.add_argument("--input", required=True)
    seed = sub.add_parser("seed")
    seed.add_argument("--input", required=True)
    args = parser.parse_args()
    path = args.data.expanduser().resolve()
    if args.command == "serve":
        with locked(path):
            if not path.exists():
                write(path, blank())
        server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(path))
        print(f"Daily journal: http://127.0.0.1:{server.server_port}/", flush=True)
        server.serve_forever()
    elif args.command == "show":
        with locked(path):
            print(json.dumps(read(path), ensure_ascii=False, indent=2))
    elif args.command == "seed":
        sample = json.loads(Path(args.input).read_text(encoding="utf-8"))
        if sample.get("version") != 1:
            raise SystemExit("Invalid sample")
        with locked(path):
            data = read(path)
            if data["entries"]:
                raise SystemExit("Journal is not empty; sample was not imported")
            write(path, sample)
    elif args.command in {"import", "compose"}:
        raw = os.sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        with locked(path):
            data = read(path)
            result = import_events(data, json.loads(raw)) if args.command == "import" else compose(data, json.loads(raw))
            write(path, data)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
