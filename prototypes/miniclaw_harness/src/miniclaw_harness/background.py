from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from typing import Any

from .store import MiniClawStore


class BackgroundTaskManager:
    def __init__(self, store: MiniClawStore):
        self.store = store
        self.tasks: dict[str, dict[str, Any]] = {}
        self._notifications: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def run(self, group_id: str, command: str, operation: Callable[[], str]) -> str:
        task_id = str(uuid.uuid4())[:8]
        self.tasks[task_id] = {
            "id": task_id,
            "group_id": group_id,
            "command": command,
            "status": "running",
            "result": None,
        }
        thread = threading.Thread(
            target=self._execute,
            args=(task_id, operation),
            daemon=True,
        )
        thread.start()
        return task_id

    def get(self, task_id: str) -> dict[str, Any]:
        return self.tasks[task_id]

    def drain_notifications(self) -> list[dict[str, Any]]:
        with self._lock:
            notifications = list(self._notifications)
            self._notifications.clear()
        return notifications

    def notifications_to_messages(self, notifications: list[dict[str, Any]]) -> list[int]:
        message_ids = []
        for notification in notifications:
            message_ids.append(
                self.store.add_inbound(
                    group_id=notification["group_id"],
                    user_id="background",
                    content=(
                        f"Background task {notification['task_id']} "
                        f"({notification['command']}) {notification['status']}: "
                        f"{notification['result']}"
                    ),
                )
            )
        return message_ids

    def _execute(self, task_id: str, operation: Callable[[], str]) -> None:
        task = self.tasks[task_id]
        try:
            result = operation()
            status = "completed"
        except Exception as exc:
            result = f"Error: {exc}"
            status = "error"

        task["status"] = status
        task["result"] = result

        with self._lock:
            self._notifications.append(
                {
                    "task_id": task_id,
                    "group_id": task["group_id"],
                    "command": task["command"],
                    "status": status,
                    "result": result,
                }
            )
