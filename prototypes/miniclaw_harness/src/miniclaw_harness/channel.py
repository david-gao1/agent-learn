from __future__ import annotations

from .store import MiniClawStore


class LocalChannel:
    def __init__(self, store: MiniClawStore):
        self.store = store

    def send(self, group_id: str, user_id: str, content: str) -> int:
        return self.store.add_inbound(group_id=group_id, user_id=user_id, content=content)
