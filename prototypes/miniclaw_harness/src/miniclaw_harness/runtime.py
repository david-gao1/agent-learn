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
