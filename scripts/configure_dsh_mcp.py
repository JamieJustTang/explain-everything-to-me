#!/usr/bin/env python3
"""Connect sivtr's read-only MCP server to every Dsh profile."""

import argparse
import os
import shutil
from pathlib import Path


ROW_ID = "mcp-explain-everything-sivtr"


def find_sivtr(home: Path) -> Path | None:
    found = shutil.which("sivtr")
    if found:
        return Path(found).resolve()
    candidate = home / ".local" / "bin" / "sivtr"
    return candidate.resolve() if candidate.is_file() and os.access(candidate, os.X_OK) else None


def configure(dsh_home: Path, executable: Path) -> Path:
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise SystemExit(f"sivtr executable is not available: {executable}")
    path = dsh_home / "cordis.patch.yml"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if ROW_ID in existing or "serverName: sivtr" in existing:
        print(f"Dsh already has a sivtr MCP row: {path}")
        return path
    lines = [line.strip() for line in existing.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if lines and lines != ["[]"] and not lines[0].startswith("- "):
        raise SystemExit(f"Unsupported Dsh patch format; add the MCP row manually: {path}")
    # Dsh patch files are YAML sequences. Quote the executable path as a YAML scalar.
    import json

    block = (
        "# explain-everything-to-me: sivtr MCP runs in the Dsh host, outside bash's workspace sandbox.\n"
        "- insert:\n"
        f"    - id: {ROW_ID}\n"
        "      name: '@deepseek-ai/dsh-mcp-client'\n"
        "      config:\n"
        "        serverName: sivtr\n"
        "        transport: stdio\n"
        f"        command: {json.dumps(str(executable))}\n"
        "        args: ['mcp', 'serve']\n"
    )
    prefix = "" if not existing or lines == ["[]"] else existing.rstrip() + "\n\n"
    dsh_home.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(prefix + block, encoding="utf-8")
    temporary.replace(path)
    print(f"Configured Dsh sivtr MCP: {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsh-home", type=Path, default=Path(os.environ.get("DSH_HOME", "~/.dsh")).expanduser())
    parser.add_argument("--sivtr", type=Path, help="Absolute sivtr executable path; auto-detected otherwise")
    args = parser.parse_args()
    executable = args.sivtr or find_sivtr(Path.home())
    if not executable:
        raise SystemExit("sivtr was not found; install it first, then run this script again")
    configure(args.dsh_home.expanduser().resolve(), executable.expanduser().resolve())


if __name__ == "__main__":
    main()
