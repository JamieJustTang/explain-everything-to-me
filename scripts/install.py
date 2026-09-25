#!/usr/bin/env python3
"""Install the shared skill with an explicit user command for one supported host."""

import argparse
import os
import shutil
from pathlib import Path


NAME = "explain-everything-to-me"
SOURCE = Path(__file__).resolve().parents[1]
USER_ONLY = ("claude", "dsh", "grok")


def copy_bundle(destination: Path, *, user_only: bool) -> None:
    if destination.exists():
        raise SystemExit(f"Target already exists; review it before replacing: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, destination, ignore=shutil.ignore_patterns(".git", ".DS_Store", "__pycache__", "*.pyc"))
    if user_only:
        skill = destination / "SKILL.md"
        content = skill.read_text(encoding="utf-8")
        if not content.startswith("---\n"):
            raise SystemExit("SKILL.md has no YAML frontmatter")
        content = content.replace("---\n", "---\ndisable-model-invocation: true\nuser-invocable: true\n", 1)
        skill.write_text(content, encoding="utf-8")


def write_new(path: Path, content: str) -> None:
    if path.exists():
        raise SystemExit(f"Command already exists; review it before replacing: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, choices=("codex", "claude", "dsh", "gemini", "antigravity", "grok", "pi"))
    parser.add_argument("--home", type=Path, default=Path.home(), help="Override home directory (also useful for a test install)")
    parser.add_argument("--workspace", type=Path, help="Required for Antigravity; install into this workspace")
    args = parser.parse_args()
    home = args.home.expanduser().resolve()

    if args.host == "antigravity":
        if not args.workspace:
            parser.error("--workspace is required for Antigravity")
        root = args.workspace.expanduser().resolve() / ".agents"
        bundle = root / "explain-everything-to-me"
        command = root / "workflows" / f"{NAME}.md"
    elif args.host == "gemini":
        bundle = home / ".gemini" / NAME
        command = home / ".gemini" / "commands" / f"{NAME}.toml"
    elif args.host == "pi":
        bundle = home / ".pi" / "agent" / NAME
        command = home / ".pi" / "agent" / "prompts" / f"{NAME}.md"
    else:
        roots = {
            "codex": home / ".codex" / "skills",
            "claude": home / ".claude" / "skills",
            "dsh": Path(os.environ.get("DSH_HOME", str(home / ".dsh"))).expanduser().resolve() / "skills",
            "grok": home / ".grok" / "skills",
        }
        bundle = roots[args.host] / NAME
        command = None

    if bundle.exists() or (command and command.exists()):
        raise SystemExit(f"Existing installation found: {bundle if bundle.exists() else command}")
    copy_bundle(bundle, user_only=args.host in USER_ONLY)
    skill_path = bundle / "SKILL.md"
    if args.host == "gemini":
        # JSON strings are also valid TOML basic strings.
        import json
        prompt = f"Read the current Skill file at {skill_path} on every invocation, then follow it. Obey any user limit on evidence sources. This is an explicit user command. User request: {{{{args}}}}"
        write_new(command, 'description = "Explain agent work from sivtr memory"\n' + f"prompt = {json.dumps(prompt, ensure_ascii=False)}\n")
    elif args.host == "antigravity":
        write_new(command, f"---\ndescription: Explain agent work from sivtr memory\n---\n\nRead the current Skill file at `{skill_path}` on every invocation, then follow it. Obey any user limit on evidence sources. This workflow runs only when the user invokes `/{NAME}`. Treat any text after the command as the user's request. If there is no text, use the Skill's default request.\n")
    elif args.host == "pi":
        write_new(command, f"---\ndescription: Explain agent work from sivtr memory\n---\n\nRead the current Skill file at `{skill_path}` on every invocation, even if you read it earlier in this conversation; then follow it. This is an explicit user command. Answer in the user's language. Obey any user limit on evidence sources: when the user says only the archive, do not inspect repository files or Git. If the request gives a WorkRef and sivtr MCP is unavailable, run `sivtr show WORKREF --json --cwd \"$PWD\"` from the current workspace; never guess the cwd or run `sivtr_search` or bare `sivtr` as shell commands. If the request is only to show learned language rules, run `python3 {bundle / 'scripts' / 'language_memory.py'} show` and report its actual output; Skill instructions are not learned rules. User request: $@\n")

    invocation = {"codex": f"${NAME}", "pi": f"/{NAME}"}.get(args.host, f"/{NAME}")
    print(f"Installed {args.host}: {bundle}")
    print(f"Invoke with: {invocation}")
    if command:
        print(f"Command adapter: {command}")
    print("Optional: tell the agent your working language, role, familiar fields, usual meaning of 'recent', and maximum sessions per answer.")
    print("Optional Jev reranking: install jev-rag-retrieval and configure your own TYPESAFE_API_KEY in a private environment file; never put the key in chat or this repository.")


if __name__ == "__main__":
    main()
