#!/usr/bin/env python3
"""Install the pinned sivtr fork in a private, shared location."""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


FORK_URL = "https://github.com/JamieJustTang/sivtr.git"
FORK_COMMIT = "563ac3c283bd6accaf6529bcf31c687c7c6c50cd"


def install(home: Path) -> Path:
    root = home / ".local" / "share" / "explain-everything-to-me" / "sivtr"
    executable_name = "sivtr.exe" if os.name == "nt" else "sivtr"
    executable = root / "bin" / executable_name
    receipt = root / "source.json"
    expected = {"url": FORK_URL, "commit": FORK_COMMIT}
    if executable.is_file() and os.access(executable, os.X_OK) and receipt.is_file():
        try:
            if json.loads(receipt.read_text(encoding="utf-8")) == expected:
                help_result = subprocess.run([str(executable), "search", "--help"], capture_output=True, text=True, check=True)
                if "archive:" in help_result.stdout:
                    print(f"Using pinned sivtr fork: {executable}")
                    return executable
        except (ValueError, OSError, subprocess.CalledProcessError):
            pass

    cargo = shutil.which("cargo")
    if not cargo:
        raise RuntimeError("Rust cargo is required for the pinned sivtr fork. Install Rust 1.95+ or pass --sivtr /path/to/patched/sivtr.")
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sivtr-build-", dir=root) as staging:
        command = [cargo, "install", "--git", FORK_URL, "--rev", FORK_COMMIT,
                   "--locked", "--root", staging, "--bin", "sivtr", "sivtr"]
        print(f"Building pinned sivtr fork at {FORK_COMMIT[:12]} (first install may take several minutes)...", flush=True)
        subprocess.run(command, check=True)
        built = Path(staging) / "bin" / executable_name
        if not built.is_file() or not os.access(built, os.X_OK):
            raise RuntimeError("cargo finished without an executable sivtr binary")
        help_result = subprocess.run([str(built), "search", "--help"], capture_output=True, text=True, check=True)
        if "archive:" not in help_result.stdout:
            raise RuntimeError("the built sivtr does not expose archive: search")
        executable.parent.mkdir(parents=True, exist_ok=True)
        os.replace(built, executable)
        temporary = receipt.with_suffix(".tmp")
        temporary.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, receipt)
    print(f"Installed pinned sivtr fork: {executable}")
    return executable


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    args = parser.parse_args()
    try:
        install(args.home.expanduser().resolve())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"sivtr fork installation failed: {exc}") from exc


if __name__ == "__main__":
    main()
