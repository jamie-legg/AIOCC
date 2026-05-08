#!/usr/bin/env python3
"""Start the simplified Upload Studio stack."""

import signal
import subprocess
import sys
import time
from pathlib import Path


def start_process(name: str, command: list[str], cwd: Path) -> subprocess.Popen:
    print(f"[{name}] starting: {' '.join(command)}")
    return subprocess.Popen(command, cwd=cwd)


def npm_command() -> str:
    """Return the npm executable name for the current platform."""
    return "npm.cmd" if sys.platform.startswith("win") else "npm"


def main() -> int:
    root_dir = Path(__file__).parent.parent
    upload_studio_dir = root_dir / "upload-studio"

    processes: list[tuple[str, subprocess.Popen]] = []

    def shutdown(*_: object) -> None:
        print("\n[shutdown] stopping Upload Studio stack")
        for name, process in processes:
            if process.poll() is None:
                print(f"[{name}] terminate")
                process.terminate()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        processes.append(
            (
                "api",
                start_process(
                    "api",
                    ["uv", "run", "python", "-m", "uvicorn", "backend.src.main:app", "--host", "0.0.0.0", "--port", "8000"],
                    root_dir,
                ),
            )
        )
        processes.append(("upload-studio", start_process("upload-studio", [npm_command(), "run", "dev"], upload_studio_dir)))

        print("\nUpload Studio is starting:")
        print("  API: http://localhost:8000")
        print("  UI:  http://localhost:5173")
        print("\nPress Ctrl+C to stop both services.\n")

        while True:
            for name, process in processes:
                code = process.poll()
                if code is not None:
                    print(f"[{name}] exited with code {code}")
                    shutdown()
                    return code
            time.sleep(0.5)
    finally:
        shutdown()


if __name__ == "__main__":
    sys.exit(main())
