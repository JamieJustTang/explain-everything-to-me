#!/usr/bin/env python3
"""Connect the local sivtr MCP server to a supported agent host."""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from configure_dsh_mcp import configure as configure_dsh
from configure_dsh_mcp import find_sivtr


NATIVE_COMMANDS = {
    "codex": lambda exe: ["codex", "mcp", "add", "sivtr", "--", str(exe), "mcp", "serve"],
    "claude": lambda exe: ["claude", "mcp", "add", "--scope", "user", "sivtr", "--", str(exe), "mcp", "serve"],
    "gemini": lambda exe: ["gemini", "mcp", "add", "--scope", "user", "sivtr", str(exe), "mcp", "serve"],
    "grok": lambda exe: ["grok", "mcp", "add", "--scope", "user", "sivtr", "--", str(exe), "mcp", "serve"],
}


def configured(host: str, home: Path) -> bool:
    path = {
        "codex": home / ".codex" / "config.toml",
        "claude": home / ".claude.json",
        "gemini": home / ".gemini" / "settings.json",
        "grok": home / ".grok" / "config.toml",
        "antigravity": home / ".gemini" / "config" / "mcp_config.json",
    }[host]
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    if path.suffix == ".toml":
        return bool(re.search(r'^\s*\[\s*mcp_servers\.(?:sivtr|"sivtr")\s*\]', content, re.MULTILINE))
    data = json.loads(content)
    if not isinstance(data, dict) or not isinstance(data.get("mcpServers", {}), dict):
        raise ValueError(f"Invalid MCP config: {path}")
    return "sivtr" in data.get("mcpServers", {})


def configure_antigravity(home: Path, executable: Path) -> None:
    path = home / ".gemini" / "config" / "mcp_config.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(data, dict) or not isinstance(data.get("mcpServers", {}), dict):
        raise ValueError(f"Invalid Antigravity MCP config: {path}")
    data.setdefault("mcpServers", {})["sivtr"] = {"command": str(executable), "args": ["mcp", "serve"]}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    print(f"Configured Antigravity sivtr MCP: {path}")


def update_existing(host: str, home: Path, executable: Path) -> None:
    if host == "antigravity":
        configure_antigravity(home, executable)
        return
    path = {
        "codex": home / ".codex" / "config.toml",
        "claude": home / ".claude.json",
        "gemini": home / ".gemini" / "settings.json",
        "grok": home / ".grok" / "config.toml",
    }[host]
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        server = data["mcpServers"]["sivtr"]
        if not isinstance(server, dict):
            raise ValueError(f"Invalid sivtr MCP entry: {path}")
        server.update({"command": str(executable), "args": ["mcp", "serve"]})
        updated = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    else:
        content = path.read_text(encoding="utf-8")
        section = re.search(r'(?ms)^\[mcp_servers\.(?:sivtr|"sivtr")\]\n(.*?)(?=^\[|\Z)', content)
        if not section:
            raise ValueError(f"Invalid sivtr MCP section: {path}")
        body, count = re.subn(r'(?m)^command\s*=.*$', lambda _: f'command = {json.dumps(str(executable))}', section.group(1), count=1)
        if count != 1:
            raise ValueError(f"sivtr MCP command is missing: {path}")
        updated = content[:section.start(1)] + body + content[section.end(1):]
    if updated != path.read_text(encoding="utf-8"):
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(updated, encoding="utf-8")
        temporary.replace(path)
        print(f"Updated {host} sivtr MCP: {path}")
    else:
        print(f"{host} sivtr MCP already uses: {executable}")


def configure(host: str, home: Path, executable: Path) -> None:
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ValueError(f"sivtr executable is not available: {executable}")
    if host == "dsh":
        configure_dsh(Path(os.environ.get("DSH_HOME", str(home / ".dsh"))).expanduser().resolve(), executable)
        return
    if host == "pi":
        print("Pi core has no built-in MCP client; keep using the sivtr CLI or install a trusted Pi MCP extension.")
        return
    if configured(host, home):
        update_existing(host, home, executable)
        return
    if host == "antigravity":
        configure_antigravity(home, executable)
        return
    env = os.environ.copy()
    env["HOME"] = str(home)
    if host == "codex":
        env["CODEX_HOME"] = str(home / ".codex")
        (home / ".codex").mkdir(parents=True, exist_ok=True)
    result = subprocess.run(NATIVE_COMMANDS[host](executable), env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{host} MCP command failed (exit {result.returncode}): {result.stderr.strip()[-500:]}")
    if not configured(host, home):
        raise RuntimeError(f"{host} CLI exited successfully but sivtr MCP was not found in the user config")
    print(f"Configured {host} sivtr MCP with its native CLI.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, choices=(*NATIVE_COMMANDS, "antigravity", "dsh", "pi"))
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--sivtr", type=Path, help="Absolute sivtr executable path; auto-detected otherwise")
    args = parser.parse_args()
    home = args.home.expanduser().resolve()
    executable = args.sivtr or find_sivtr(home)
    if not executable:
        raise SystemExit("sivtr was not found; install it first, then run this script again")
    configure(args.host, home, executable.expanduser().resolve())


if __name__ == "__main__":
    main()
