from __future__ import annotations

from typing import Protocol


class CompletionModel(Protocol):
    def complete(self, instructions: str, prompt: str) -> str:
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
    def __init__(self):
        self.main_context: list[str] = []
        self.child_contexts: list[list[str]] = []

    def respond(self, message: dict) -> str:
        content = message["content"]
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
