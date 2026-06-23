from __future__ import annotations

import json
import uuid
from pathlib import Path


class TaskStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def add(self, title: str) -> str:
        tasks = self.list()
        task_id = str(uuid.uuid4())[:8]
        tasks.append({"id": task_id, "title": title, "status": "open"})
        self._write(tasks)
        return task_id

    def update(self, task_id: str, status: str) -> None:
        tasks = self.list()
        for task in tasks:
            if task["id"] == task_id:
                task["status"] = status
                self._write(tasks)
                return
        raise KeyError(f"Task not found: {task_id}")

    def list(self) -> list[dict[str, str]]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, tasks: list[dict[str, str]]) -> None:
        self.path.write_text(
            json.dumps(tasks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
