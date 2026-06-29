from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .background import BackgroundTaskManager
from .tools import BashTool, FileTool


class CompletionModel(Protocol):
    def complete(self, instructions: str, prompt: str) -> str:
        ...


class FileListingTool(Protocol):
    def list_files(self, limit: int = 20) -> list[str]:
        ...

    def read_file(self, relative_path: str, max_chars: int = 1200) -> str:
        ...


class CommandTool(Protocol):
    def run(self, command: str) -> str:
        ...


@dataclass(frozen=True)
class ToolDecision:
    action: str
    target: str
    reason: str


class TaskBlockedError(RuntimeError):
    pass


class LocalAgentRuntime:
    def respond(self, message: dict) -> str:
        return (
            "MiniClaw processed message "
            f"#{message['id']} for group {message['group_id']}: {message['content']}"
        )


class ModelBackedRuntime:
    def __init__(self, model: CompletionModel):
        self.model = model

    def respond(self, message: dict) -> str:
        return self.model.complete(
            instructions=(
                "You are the MiniClaw agent runtime inside a local Harness product. "
                "Respond concisely and focus on the user's requested task."
            ),
            prompt=(
                f"Group: {message['group_id']}\n"
                f"User: {message['user_id']}\n"
                f"Message: {message['content']}"
            ),
        )


class SubAgentRuntime:
    def __init__(
        self,
        background: BackgroundTaskManager | None = None,
        workspace: Path | None = None,
        file_tool: FileListingTool | None = None,
        bash_tool: CommandTool | None = None,
        planner: CompletionModel | None = None,
    ):
        self.background = background
        self.file_tool = file_tool or (FileTool(Path(workspace)) if workspace else None)
        self.bash_tool = bash_tool or (BashTool(Path(workspace)) if workspace else None)
        self.planner = planner
        self.main_context: list[str] = []
        self.child_contexts: list[list[str]] = []
        self.decisions: list[ToolDecision] = []

    def respond(self, message: dict) -> str:
        content = message["content"]
        if "subagent-background:" in content:
            return self._dispatch_background_child(message)

        if "subagent:" not in content:
            response = (
                "MiniClaw processed message "
                f"#{message['id']} for group {message['group_id']}: {content}"
            )
            self.main_context.append(response)
            return response

        task = content.split("subagent:", 1)[1].strip()
        child_context = self._run_child(task)
        self.child_contexts.append(child_context)

        summary = f"SubAgent summary: completed isolated task '{task}'"
        self.main_context.append(summary)
        return summary

    def _run_child(self, task: str) -> list[str]:
        return [
            task,
            "child detail: inspected isolated context",
            "child detail: produced summary only",
        ]

    def resume_background_task(self, task_id: str, task: str) -> None:
        if self.background is None:
            raise RuntimeError("SubAgent background resume requires a background manager")
        decision = self._decide_tool(task)
        if decision.action != "analyze_repo":
            raise ValueError(f"resume is not supported for action: {decision.action}")
        self.background.store.add_execution_trace(
            task_id=task_id,
            event_type="plan",
            content=f"Resume isolated SubAgent background work for task: {task}",
        )
        self.background.resume_existing(
            task_id,
            lambda active_task_id: self._background_result(active_task_id, task, decision),
            pass_task_id=True,
        )

    def _dispatch_background_child(self, message: dict[str, Any]) -> str:
        if self.background is None:
            raise RuntimeError("SubAgent background dispatch requires a background manager")

        task = message["content"].split("subagent-background:", 1)[1].strip()
        child_context = self._run_child(task)
        self.child_contexts.append(child_context)
        decision = self._decide_tool(task)
        self.decisions.append(decision)

        task_id = self.background.run(
            group_id=message["group_id"],
            command=f"subagent: {task}",
            operation=lambda active_task_id: self._background_result(active_task_id, task, decision),
            start=False,
            pass_task_id=True,
        )
        self.background.store.add_execution_trace(
            task_id=task_id,
            event_type="plan",
            content=f"Plan isolated SubAgent background work for task: {task}",
        )
        self.background.store.add_tool_decision(
            task_id=task_id,
            action=decision.action,
            target=decision.target,
            reason=decision.reason,
        )
        self.background.store.add_execution_trace(
            task_id=task_id,
            event_type="decision",
            content=(
                f"{decision.action}\n"
                f"target: {decision.target}\n"
                f"reason: {decision.reason}"
            ),
        )
        self.background.store.add_execution_trace(
            task_id=task_id,
            event_type="tool_call",
            content=self._tool_call_trace(decision),
        )
        self.background.start(
            task_id,
            lambda active_task_id: self._background_result(active_task_id, task, decision),
            pass_task_id=True,
        )
        deadline = time.time() + 2
        while time.time() < deadline:
            background_task = self.background.get(task_id)
            if background_task["status"] != "running":
                break
            time.sleep(0.01)
        background_task = self.background.get(task_id)
        if background_task["status"] != "running" and background_task["result"]:
            if decision.action != "analyze_repo":
                self.background.store.add_execution_trace(
                    task_id=task_id,
                    event_type="observation",
                    content=self._observation_summary(background_task["result"]),
                )
            self.background.store.add_execution_trace(
                task_id=task_id,
                event_type="final_result",
                content=background_task["result"],
            )

        summary = f"SubAgent background task {task_id}: dispatched isolated task '{task}'"
        self.main_context.append(summary)
        return summary

    def _background_result(self, task_id: str, task: str, decision: ToolDecision) -> str:
        if decision.action == "analyze_repo":
            result = self._run_repo_analysis_task(task_id, task)
        elif decision.action == "run_tests":
            result = self._run_test_task(task, decision)
        elif decision.action == "read_file":
            result = self._run_file_read_task(task, decision)
        elif decision.action == "list_files":
            result = self._run_file_list_task(task, decision, include_preview=False)
        else:
            result = self._run_file_list_task(task, decision, include_preview=True, include_bash=True)
        return result

    def _observation_summary(self, result: str) -> str:
        markers = [
            "Test command output:",
            "Observed workspace files:",
            "First file preview",
            "Bash pwd:",
        ]
        for marker in markers:
            if marker in result:
                return result[result.index(marker) :].strip()
        return result

    def _tool_call_trace(self, decision: ToolDecision) -> str:
        if decision.action == "analyze_repo":
            return "FileTool.list_files: workspace"
        if decision.action == "run_tests":
            return f"BashTool.run: {decision.target}"
        if decision.action == "read_file":
            return f"FileTool.read_file: {decision.target}"
        if decision.action == "list_files":
            return f"FileTool.list_files: {decision.target}"
        return f"Inspect workspace: {decision.target}"

    def _trace(self, task_id: str, event_type: str, content: str) -> None:
        if self.background is None:
            return
        self.background.store.add_execution_trace(
            task_id,
            event_type,
            content,
            compact_threshold=20,
            keep_recent=8,
        )

    def _run_repo_analysis_task(self, task_id: str, task: str) -> str:
        if self.file_tool is None or self.bash_tool is None:
            return "Repo analysis summary: workspace tools are unavailable."

        plan = self._plan_repo_analysis(task_id, task)
        existing_state = self._load_task_state(task_id)
        files = existing_state.get("files") if isinstance(existing_state.get("files"), list) else None
        preview_file = str(existing_state.get("preview_file", ""))
        preview = str(existing_state.get("preview", ""))

        if files is not None and preview_file and preview:
            self._trace(
                task_id,
                "observation",
                f"Reused task state: files={', '.join(files)}; preview_file={preview_file}",
            )
        else:
            files = []
            preview = ""
            preview_file = ""
            if "list_files" in plan:
                files = self.file_tool.list_files(limit=20)
                observed = ", ".join(files) if files else "(none)"
                self._trace(task_id, "observation", f"Observed workspace files: {observed}")
            if "read_file" in plan:
                preview_file = files[0] if files else ""
                if preview_file:
                    self._trace(task_id, "tool_call", f"FileTool.read_file: {preview_file}")
                    preview = self.file_tool.read_file(preview_file, max_chars=400)
                    self._trace(task_id, "observation", f"First file preview ({preview_file}): {preview}")

        test_output = ""
        if "run_tests" in plan:
            self._trace(task_id, "tool_call", "BashTool.run: python3 -m unittest discover -s tests -v")
            test_output = self.bash_tool.run("python3 -m unittest discover -s tests -v")
            self._trace(task_id, "observation", f"Test command output: {test_output}")
        observed = ", ".join(files) if files else "(none)"
        test_failed = test_output.startswith("exit ")

        summary = (
            "Repo analysis summary: "
            f"files={observed}; "
            f"preview={preview}; "
            f"tests={test_output}"
        )
        self._persist_repo_analysis_state(
            task_id=task_id,
            files=files,
            preview_file=preview_file,
            preview=preview,
            test_output=test_output,
            summary=summary,
            plan_source="model" if self.planner is not None else "rule",
        )
        if test_failed:
            raise TaskBlockedError(f"repo analysis blocked by failing tests: {test_output}")
        return summary

    def _plan_repo_analysis(self, task_id: str, task: str) -> list[str]:
        fallback = ["list_files", "read_file", "run_tests", "summarize"]
        if self.planner is None:
            return fallback
        response = self.planner.complete(
            instructions=(
                "You are planning MiniClaw repository analysis. "
                "Only return JSON with a steps array. Allowed steps: "
                "list_files, read_file, run_tests, summarize."
            ),
            prompt=f"Task id: {task_id}\nTask: {task}",
        )
        parsed = json.loads(response)
        steps = parsed.get("steps", [])
        allowed = {"list_files", "read_file", "run_tests", "summarize"}
        plan = [step for step in steps if step in allowed]
        if not plan:
            plan = fallback
        self._trace(task_id, "model_plan", " -> ".join(plan))
        return plan

    def _load_task_state(self, task_id: str) -> dict[str, Any]:
        if self.background is None:
            return {}
        try:
            return self.background.store.get_task_state(task_id)
        except KeyError:
            return {}

    def _persist_repo_analysis_state(
        self,
        task_id: str,
        files: list[str],
        preview_file: str,
        preview: str,
        test_output: str,
        summary: str,
        plan_source: str = "rule",
    ) -> None:
        if self.background is None:
            return
        self.background.store.set_task_state(
            task_id,
            {
                "kind": "repo_analysis",
                "files": files,
                "preview_file": preview_file,
                "preview": preview,
                "status": "blocked" if test_output.startswith("exit ") else "completed",
                "test_status": "failed" if test_output.startswith("exit ") else "completed",
                "test_output": test_output,
                "summary": summary,
                "plan_source": plan_source,
                **(
                    {"blocked_reason": test_output}
                    if test_output.startswith("exit ")
                    else {}
                ),
            },
        )

    def _run_file_list_task(
        self,
        task: str,
        decision: ToolDecision,
        include_preview: bool,
        include_bash: bool = False,
    ) -> str:
        if self.file_tool is None:
            return f"SubAgent background result: completed isolated task '{task}'"

        observed_files = self.file_tool.list_files(limit=20)
        observed = ", ".join(observed_files) if observed_files else "(none)"
        preview = ""
        if include_preview and observed_files:
            preview = (
                f" First file preview ({observed_files[0]}): "
                f"{self.file_tool.read_file(observed_files[0], max_chars=400)}"
            )
        bash_output = ""
        if include_bash and self.bash_tool is not None:
            bash_output = f" Bash pwd: {self.bash_tool.run('pwd')}"
        return (
            f"SubAgent background result: completed isolated task '{task}'. "
            f"Decision: {decision.action} {decision.target} because {decision.reason}. "
            f"Observed workspace files: {observed}.{preview}{bash_output}"
        )

    def _run_file_read_task(self, task: str, decision: ToolDecision) -> str:
        return self._run_file_list_task(task, decision, include_preview=True, include_bash=False)

    def _run_test_task(self, task: str, decision: ToolDecision) -> str:
        if self.bash_tool is None:
            return f"SubAgent background result: completed isolated task '{task}'"
        output = self.bash_tool.run("python3 -m unittest discover -s tests -v")
        return (
            f"SubAgent background result: completed isolated task '{task}'. "
            f"Decision: {decision.action} {decision.target} because {decision.reason}. "
            f"Test command output: {output}"
        )

    def _decide_tool(self, task: str) -> ToolDecision:
        if self._wants_repo_analysis(task):
            return ToolDecision(
                action="analyze_repo",
                target="workspace",
                reason="task asks for multi-step repository analysis",
            )
        if self._wants_tests(task):
            return ToolDecision(
                action="run_tests",
                target="python3 -m unittest discover -s tests -v",
                reason="task asks to run tests",
            )
        if self._wants_file_read(task):
            return ToolDecision(
                action="read_file",
                target="first observed file",
                reason="task asks to read file content",
            )
        if self._wants_file_list(task):
            return ToolDecision(
                action="list_files",
                target="workspace",
                reason="task asks to list or summarize structure",
            )
        return ToolDecision(
            action="inspect_workspace",
            target="workspace",
            reason="default workspace inspection",
        )

    def _wants_tests(self, task: str) -> bool:
        normalized = task.lower()
        return "run tests" in normalized or "test" in normalized or "运行测试" in task

    def _wants_file_read(self, task: str) -> bool:
        normalized = task.lower()
        return "read" in normalized or "读取" in task

    def _wants_file_list(self, task: str) -> bool:
        normalized = task.lower()
        return "list" in normalized or "列出" in task or "结构" in task

    def _wants_repo_analysis(self, task: str) -> bool:
        normalized = task.lower()
        return "analyze repo" in normalized or "分析仓库" in task or "分析这个仓库" in task
