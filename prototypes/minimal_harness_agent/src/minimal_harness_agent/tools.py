import subprocess
from pathlib import Path


DANGEROUS_COMMANDS = ("rm -rf /", "sudo", "shutdown", "reboot", "> /dev/")


def read_file(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def run_bash(command: str, cwd: Path, timeout: int = 10) -> str:
    if any(dangerous in command for dangerous in DANGEROUS_COMMANDS):
        return "Error: Dangerous command blocked"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=Path(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"Error: Timeout after {timeout}s"

    output = (result.stdout + result.stderr).strip()
    return output[:50000] if output else "(no output)"
