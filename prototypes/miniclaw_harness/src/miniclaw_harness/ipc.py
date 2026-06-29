from __future__ import annotations

import json
import time
from pathlib import Path

from .scheduler import OneShotScheduler
from .store import MiniClawStore


class FileSystemIPC:
    def __init__(self, root: Path, store: MiniClawStore, scheduler: OneShotScheduler):
        self.root = Path(root)
        self.store = store
        self.scheduler = scheduler
        self.root.mkdir(parents=True, exist_ok=True)

    def ensure_group(self, group_id: str) -> Path:
        namespace = self.root / group_id
        for child in ("input", "messages", "tasks"):
            (namespace / child).mkdir(parents=True, exist_ok=True)
        return namespace

    def write_input(self, group_id: str, user_id: str, content: str) -> Path:
        namespace = self.ensure_group(group_id)
        return self._write_json(
            namespace / "input",
            {
                "group_id": group_id,
                "user_id": user_id,
                "content": content,
            },
        )

    def drain_inputs(self) -> list[int]:
        message_ids = []
        for path in sorted(self.root.glob("*/input/*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            message_ids.append(
                self.store.add_inbound(
                    group_id=payload["group_id"],
                    user_id=payload["user_id"],
                    content=payload["content"],
                )
            )
            path.unlink()
        return message_ids

    def flush_outbound(self, group_id: str) -> list[Path]:
        namespace = self.ensure_group(group_id)
        written = []
        for message in self.store.list_outbound(group_id=group_id):
            target = namespace / "messages" / f"message_{message['id']}.json"
            if target.exists():
                continue
            target.write_text(
                json.dumps(message, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            written.append(target)
        return written

    def write_task(self, group_id: str, user_id: str, content: str, run_at: float) -> Path:
        namespace = self.ensure_group(group_id)
        return self._write_json(
            namespace / "tasks",
            {
                "group_id": group_id,
                "user_id": user_id,
                "content": content,
                "run_at": run_at,
            },
        )

    def drain_tasks(self) -> list[int]:
        task_ids = []
        for path in sorted(self.root.glob("*/tasks/*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            task_ids.append(
                self.scheduler.schedule_once(
                    group_id=payload["group_id"],
                    user_id=payload["user_id"],
                    content=payload["content"],
                    run_at=payload["run_at"],
                )
            )
            path.unlink()
        return task_ids

    def _write_json(self, directory: Path, payload: dict) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{int(time.time() * 1000)}_{len(list(directory.glob('*.json')))}.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return target
