from __future__ import annotations

from .store import MiniClawStore


class OneShotScheduler:
    def __init__(self, store: MiniClawStore):
        self.store = store

    def schedule_once(self, group_id: str, user_id: str, content: str, run_at: float) -> int:
        return self.store.add_task(
            group_id=group_id,
            user_id=user_id,
            content=content,
            run_at=run_at,
        )

    def tick(self, now: float) -> list[int]:
        created_messages = []
        for task in self.store.due_tasks(now):
            message_id = self.store.add_inbound(
                group_id=task["group_id"],
                user_id=task["user_id"],
                content=task["content"],
            )
            self.store.mark_task_dispatched(task["id"], message_id)
            created_messages.append(message_id)
        return created_messages
