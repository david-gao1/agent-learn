from __future__ import annotations


class GroupQueue:
    def __init__(self):
        self.group_state: dict[str, str] = {}

    def begin(self, group_id: str) -> bool:
        if self.group_state.get(group_id) == "running":
            return False
        self.group_state[group_id] = "running"
        return True

    def finish(self, group_id: str) -> None:
        self.group_state[group_id] = "idle"
