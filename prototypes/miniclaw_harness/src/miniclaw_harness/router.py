from __future__ import annotations

from .store import MiniClawStore


class OutputRouter:
    def __init__(self, store: MiniClawStore):
        self.store = store

    def route(self, group_id: str, content: str, source_message_id: int) -> int:
        return self.store.add_outbound(
            group_id=group_id,
            content=content,
            source_message_id=source_message_id,
        )
