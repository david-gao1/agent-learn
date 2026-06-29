from __future__ import annotations

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
    ):
        self.background = background
        self.file_tool = file_tool or (FileTool(Path(workspace)) if workspace else None)
        self.bash_tool = bash_tool or (BashTool(Path(workspace)) if workspace else None)
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

    def _dispatch_background_child(self, message: dict[str, Any]) -> str:
        if self.background is None:
            raise RuntimeError("SubAgent background dispatch requires a background manager")

        task = message["content"].split("subagent-background:", 1)[1].strip()
        child_context = self._run_child(task)
        self.child_contexts.append(child_context)

        task_id = self.background.run(
            group_id=message["group_id"],
            command=f"subagent: {task}",
            operation=lambda: self._background_result(task),
        )
        deadline = time.time() + 2
        while time.time() < deadline:
            background_task = self.background.get(task_id)
            if background_task["status"] != "running":
                break
            time.sleep(0.01)

        summary = f"SubAgent background task {task_id}: dispatched isolated task '{task}'"
        self.main_context.append(summary)
        return summary

    def _background_result(self, task: str) -> str:
        decision = self._decide_tool(task)
        self.decisions.append(decision)
        if decision.action == "run_tests":
            return self._run_test_task(task, decision)
        if decision.action == "read_file":
            return self._run_file_read_task(task, decision)
        if decision.action == "list_files":
            return self._run_file_list_task(task, decision, include_preview=False)
        return self._run_file_list_task(task, decision, include_preview=True, include_bash=True)

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
