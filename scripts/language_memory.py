#!/usr/bin/env python3
"""Store language adaptations and their post-evolution reviews."""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


DEFAULT_STORE = Path.home() / ".explain-everything-to-me" / "language-memory.json"
KINDS = {"principle", "habit", "vocabulary"}


def read_store(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": 1, "entries": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("entries"), list):
        raise ValueError("unsupported language memory file")
    return data


def latest_entries(data: dict) -> dict[str, dict]:
    latest = {}
    for entry in data["entries"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not isinstance(entry.get("revision"), int):
            raise ValueError("invalid language memory entry")
        old = latest.get(entry["id"])
        if old is None or entry["revision"] > old["revision"]:
            latest[entry["id"]] = entry
        elif entry["revision"] == old["revision"]:
            raise ValueError("duplicate language memory revision")
    return latest


def effective_entries(data: dict) -> list[dict]:
    """Keep the last good version while a newer one awaits review or failed it."""
    history: dict[str, list[dict]] = {}
    for entry in data["entries"]:
        history.setdefault(entry["id"], []).append(entry)
    result = []
    for versions in history.values():
        versions.sort(key=lambda entry: entry["revision"], reverse=True)
        if versions[0].get("status") == "revoked":
            continue
        active = next((entry for entry in versions if entry.get("status") == "active"), None)
        if active:
            result.append(active)
    return result


def validate_proposal(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("proposal must be a JSON object")
    kind, scope = raw.get("kind"), raw.get("scope")
    if kind not in KINDS or scope not in {"global", "project"}:
        raise ValueError("kind or scope is invalid")
    workspace = raw.get("workspace")
    if scope == "project" and (not isinstance(workspace, str) or not workspace.strip()):
        raise ValueError("project scope needs a workspace coordinate")
    if scope == "global" and workspace is not None:
        raise ValueError("global scope must use null workspace")
    rule = raw.get("rule")
    refs = raw.get("evidence_refs")
    if not isinstance(rule, str) or not rule.strip() or not isinstance(refs, list) or not refs:
        raise ValueError("rule and evidence_refs are required")
    if not all(isinstance(ref, str) and ref.strip() for ref in refs):
        raise ValueError("evidence_refs must be nonempty strings")
    if raw.get("id") is not None and (not isinstance(raw["id"], str) or not raw["id"].strip()):
        raise ValueError("id must be a nonempty string")
    basis = raw.get("basis")
    if basis not in {"explicit", "repeated", "correction"}:
        raise ValueError("basis must be explicit, repeated, or correction")
    return {"kind": kind, "scope": scope, "workspace": workspace, "rule": rule.strip(), "evidence_refs": refs, "basis": basis}


def write_store(path: Path, data: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".language-memory-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.chmod(temporary, 0o600)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE, help="Override store path for testing or migration")
    commands = parser.add_subparsers(dest="command", required=True)
    show = commands.add_parser("show", help="Show reviewed rules for a workspace")
    show.add_argument("--workspace", help="Exact project coordinate; omit for global rules only")
    commands.add_parser("list", help="List the latest version of every rule for review and management")
    commands.add_parser("pending", help="Show adaptations still needing revise evaluation")
    commands.add_parser("evolve", help="Read one evidence-backed adaptation as JSON from stdin")
    revise = commands.add_parser("revise", help="Evaluate an adaptation after it was written")
    revise.add_argument("id")
    revise.add_argument("--result", choices=("pass", "fail"), required=True)
    revise.add_argument("--reason", required=True)
    revoke = commands.add_parser("revoke", help="Stop using a rule in later calls")
    revoke.add_argument("id")
    delete = commands.add_parser("delete", help="Permanently remove one rule and its history")
    delete.add_argument("id")
    args = parser.parse_args()
    data = read_store(args.store)
    latest = latest_entries(data)

    if args.command == "show":
        entries = [entry for entry in effective_entries(data) if (
            entry.get("scope") == "global" or (args.workspace and entry.get("scope") == "project" and entry.get("workspace") == args.workspace)
        )]
        print(json.dumps(sorted(entries, key=lambda entry: entry["id"]), ensure_ascii=False, indent=2))
        return

    if args.command == "list":
        print(json.dumps(sorted(latest.values(), key=lambda entry: entry["id"]), ensure_ascii=False, indent=2))
        return

    if args.command == "pending":
        entries = [entry for entry in latest.values() if entry.get("status") == "provisional"]
        print(json.dumps(sorted(entries, key=lambda entry: entry["id"]), ensure_ascii=False, indent=2))
        return

    if args.command == "evolve":
        proposal = json.load(sys.stdin)
        clean = validate_proposal(proposal)
        entry_id = proposal.get("id") or str(uuid4())
        previous = latest.get(entry_id)
        if previous and previous.get("status") == "revoked":
            raise ValueError("revoked rule needs a new id")
        if previous and previous.get("status") == "provisional":
            raise ValueError("revise the pending version before evolving it again")
        if not previous and any(
            entry.get("status") in {"active", "provisional"}
            and all(entry.get(key) == clean[key] for key in ("scope", "workspace", "kind", "rule"))
            for entry in latest.values()
        ):
            raise ValueError("this adaptation already exists")
        entry = {
            "id": entry_id,
            "revision": previous["revision"] + 1 if previous else 1,
            "status": "provisional",
            **clean,
            "evolved_at": datetime.now(timezone.utc).isoformat(),
        }
        data["entries"].append(entry)
        write_store(args.store, data)
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        return

    if args.command == "revise":
        entry = latest.get(args.id)
        if entry is None or entry.get("status") != "provisional":
            raise ValueError("no provisional adaptation with this id")
        if not args.reason.strip():
            raise ValueError("revise reason cannot be empty")
        entry["status"] = "active" if args.result == "pass" else "quarantined"
        entry["review"] = {"result": args.result, "reason": args.reason.strip(), "at": datetime.now(timezone.utc).isoformat()}
        write_store(args.store, data)
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        return

    previous = latest.get(args.id)
    if previous is None:
        raise ValueError("unknown rule id")
    if args.command == "revoke":
        active = next((entry for entry in effective_entries(data) if entry["id"] == args.id), None)
        if active is None:
            raise ValueError("rule is not active")
        entry = {**active, "revision": previous["revision"] + 1, "status": "revoked", "revoked_at": datetime.now(timezone.utc).isoformat()}
        data["entries"].append(entry)
    else:
        data["entries"] = [entry for entry in data["entries"] if entry.get("id") != args.id]
    write_store(args.store, data)
    print(args.id)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
