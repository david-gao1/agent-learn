from __future__ import annotations


class LocalAgentRuntime:
    def respond(self, message: dict) -> str:
        return (
            "MiniClaw processed message "
            f"#{message['id']} for group {message['group_id']}: {message['content']}"
        )
