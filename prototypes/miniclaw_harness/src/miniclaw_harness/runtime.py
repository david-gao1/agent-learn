from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Protocol

from .background import BackgroundTaskManager
from .tools import FileTool


class CompletionModel(Protocol):
    def complete(self, instructions: str, prompt: str) -> str:
        ...


class FileListingTool(Protocol):
    def list_files(self, limit: int = 20) -> list[str]:
        ...


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
    ):
        self.background = background
        self.file_tool = file_tool or (FileTool(Path(workspace)) if workspace else None)
        self.main_context: list[str] = []
        self.child_contexts: list[list[str]] = []

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
        if self.file_tool is None:
            return f"SubAgent background result: completed isolated task '{task}'"

        observed_files = self.file_tool.list_files(limit=20)
        observed = ", ".join(observed_files) if observed_files else "(none)"
        return (
            f"SubAgent background result: completed isolated task '{task}'. "
            f"Observed workspace files: {observed}"
        )
