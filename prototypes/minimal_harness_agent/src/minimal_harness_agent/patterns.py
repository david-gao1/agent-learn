from __future__ import annotations

import contextlib
import io
from pathlib import Path
from typing import Any, Callable


def run_plan_act(
    goal: str,
    steps: list[str],
    act: Callable[[str], str],
) -> dict[str, Any]:
    observations = []
    for step in steps:
        observations.append({"step": step, "observation": act(step)})

    return {
        "goal": goal,
        "status": "done",
        "observations": observations,
    }


def run_reflection(
    produce: Callable[[], str],
    critique: Callable[[str], str],
    max_retries: int = 1,
) -> dict[str, Any]:
    critiques = []
    output = ""

    for _ in range(max_retries + 1):
        output = produce()
        issue = critique(output)
        critiques.append(issue)
        if not issue:
            return {"status": "accepted", "output": output, "critiques": critiques}

    return {"status": "needs_review", "output": output, "critiques": critiques}


def execute_codeact(code: str, workspace: Path) -> dict[str, Any]:
    if "import " in code or "__" in code or "open(" in code:
        return {"status": "blocked", "error": "CodeAct blocked by safety policy"}

    namespace = {
        "workspace": Path(workspace),
        "len": len,
        "list": list,
        "str": str,
        "sorted": sorted,
    }
    stdout = io.StringIO()

    try:
        with contextlib.redirect_stdout(stdout):
            exec(code, {"__builtins__": {}}, namespace)
    except Exception as exc:
        return {"status": "error", "error": str(exc), "stdout": stdout.getvalue()}

    return {
        "status": "ok",
        "result": namespace.get("result"),
        "stdout": stdout.getvalue(),
    }
