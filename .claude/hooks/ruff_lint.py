"""PostToolUse hook: run ruff check on src/ or tests/ after .py file changes."""

import json
import os
import subprocess
import sys


def main() -> None:
    data = json.load(sys.stdin)
    file_path = data.get("tool_input", {}).get("file_path", "").replace(os.sep, "/")

    if not file_path.endswith(".py"):
        return

    if "/src/" in file_path or file_path.startswith("src/"):
        target = "src/"
    elif "/tests/" in file_path or file_path.startswith("tests/"):
        target = "tests/"
    else:
        return

    result = subprocess.run(
        ["uv", "run", "ruff", "check", target],
        capture_output=True,
        text=True,
    )
    if result.stdout.strip():
        print(result.stdout.strip())


if __name__ == "__main__":
    main()
