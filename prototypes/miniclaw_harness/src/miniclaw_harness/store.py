from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


class MiniClawStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        with self._lock:
            self.conn.executescript(
                """
                create table if not exists messages (
                    id integer primary key autoincrement,
                    group_id text not null,
                    user_id text not null,
                    direction text not null,
                    content text not null,
                    status text not null,
                    source_message_id integer,
                    created_at real not null default (strftime('%s', 'now'))
                );

                create table if not exists tasks (
                    id integer primary key autoincrement,
                    group_id text not null,
                    user_id text not null,
                    content text not null,
                    run_at real not null,
                    status text not null,
                    created_message_id integer
                );

                create table if not exists background_tasks (
                    id text primary key,
                    group_id text not null,
                    command text not null,
                    status text not null,
                    result text
                );

                create table if not exists tool_decisions (
                    task_id text primary key,
                    action text not null,
                    target text not null,
                    reason text not null
                );

                create table if not exists execution_traces (
                    id integer primary key autoincrement,
                    task_id text not null,
                    event_type text not null,
                    content text not null,
                    created_at real not null default (strftime('%s', 'now'))
                );

                create table if not exists task_states (
                    task_id text primary key,
                    state_json text not null
                );
                """
            )
            self.conn.commit()

    def add_inbound(self, group_id: str, user_id: str, content: str) -> int:
        cursor = self.conn.execute(
            """
            insert into messages (group_id, user_id, direction, content, status)
            values (?, ?, 'inbound', ?, 'pending')
            """,
            (group_id, user_id, content),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def add_outbound(self, group_id: str, content: str, source_message_id: int) -> int:
        cursor = self.conn.execute(
            """
            insert into messages
                (group_id, user_id, direction, content, status, source_message_id)
            values (?, 'miniclaw', 'outbound', ?, 'ready', ?)
            """,
            (group_id, content, source_message_id),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def next_pending_message(self) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            select * from messages
            where direction = 'inbound' and status = 'pending'
            order by id asc
            limit 1
            """
        ).fetchone()
        return dict(row) if row else None

    def update_message_status(self, message_id: int, status: str) -> None:
        self.conn.execute(
            "update messages set status = ? where id = ?",
            (status, message_id),
        )
        self.conn.commit()

    def get_message(self, message_id: int) -> dict[str, Any]:
        row = self.conn.execute(
            "select * from messages where id = ?",
            (message_id,),
        ).fetchone()
        if not row:
            raise KeyError(f"message not found: {message_id}")
        return dict(row)

    def list_outbound(self, group_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            select * from messages
            where group_id = ? and direction = 'outbound'
            order by id asc
            """,
            (group_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def add_task(self, group_id: str, user_id: str, content: str, run_at: float) -> int:
        cursor = self.conn.execute(
            """
            insert into tasks (group_id, user_id, content, run_at, status)
            values (?, ?, ?, ?, 'scheduled')
            """,
            (group_id, user_id, content, run_at),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def due_tasks(self, now: float) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            select * from tasks
            where status = 'scheduled' and run_at <= ?
            order by run_at asc, id asc
            """,
            (now,),
        ).fetchall()
        return [dict(row) for row in rows]

    def mark_task_dispatched(self, task_id: int, message_id: int) -> None:
        self.conn.execute(
            """
            update tasks
            set status = 'dispatched', created_message_id = ?
            where id = ?
            """,
            (message_id, task_id),
        )
        self.conn.commit()

    def get_task(self, task_id: int) -> dict[str, Any]:
        row = self.conn.execute("select * from tasks where id = ?", (task_id,)).fetchone()
        if not row:
            raise KeyError(f"task not found: {task_id}")
        return dict(row)

    def add_background_task(
        self,
        task_id: str,
        group_id: str,
        command: str,
        status: str,
        result: str | None = None,
    ) -> None:
        with self._lock:
            self.conn.execute(
                """
                insert into background_tasks (id, group_id, command, status, result)
                values (?, ?, ?, ?, ?)
                """,
                (task_id, group_id, command, status, result),
            )
            self.conn.commit()

    def update_background_task(self, task_id: str, status: str, result: str) -> None:
        with self._lock:
            self.conn.execute(
                """
                update background_tasks
                set status = ?, result = ?
                where id = ?
                """,
                (status, result, task_id),
            )
            self.conn.commit()

    def get_background_task(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            row = self.conn.execute(
                "select * from background_tasks where id = ?",
                (task_id,),
            ).fetchone()
        if not row:
            raise KeyError(f"background task not found: {task_id}")
        return dict(row)

    def list_background_tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute(
                """
                select * from background_tasks
                order by rowid asc
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def add_tool_decision(self, task_id: str, action: str, target: str, reason: str) -> None:
        with self._lock:
            self.conn.execute(
                """
                insert or replace into tool_decisions (task_id, action, target, reason)
                values (?, ?, ?, ?)
                """,
                (task_id, action, target, reason),
            )
            self.conn.commit()

    def get_tool_decision(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            row = self.conn.execute(
                "select * from tool_decisions where task_id = ?",
                (task_id,),
            ).fetchone()
        if not row:
            raise KeyError(f"tool decision not found: {task_id}")
        return dict(row)

    def add_execution_trace(self, task_id: str, event_type: str, content: str) -> None:
        with self._lock:
            self.conn.execute(
                """
                insert into execution_traces (task_id, event_type, content)
                values (?, ?, ?)
                """,
                (task_id, event_type, content),
            )
            self.conn.commit()

    def list_execution_traces(self, task_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute(
                """
                select * from execution_traces
                where task_id = ?
                order by id asc
                """,
                (task_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def set_task_state(self, task_id: str, state: dict[str, Any]) -> None:
        with self._lock:
            self.conn.execute(
                """
                insert or replace into task_states (task_id, state_json)
                values (?, ?)
                """,
                (task_id, json.dumps(state, ensure_ascii=False, sort_keys=True)),
            )
            self.conn.commit()

    def get_task_state(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            row = self.conn.execute(
                "select state_json from task_states where task_id = ?",
                (task_id,),
            ).fetchone()
        if not row:
            raise KeyError(f"task state not found: {task_id}")
        return json.loads(row["state_json"])

    def compact_task_trace(self, task_id: str, keep_recent: int = 5) -> dict[str, Any]:
        if keep_recent < 0:
            raise ValueError("keep_recent must be non-negative")
        with self._lock:
            state = self.get_task_state(task_id)
            traces = self.list_execution_traces(task_id)
            recent = traces[-keep_recent:] if keep_recent else []
            summary = self._build_compact_summary(state, traces)
            state["compact_summary"] = summary
            self.conn.execute(
                """
                insert or replace into task_states (task_id, state_json)
                values (?, ?)
                """,
                (task_id, json.dumps(state, ensure_ascii=False, sort_keys=True)),
            )
            self.conn.execute("delete from execution_traces where task_id = ?", (task_id,))
            self.conn.execute(
                """
                insert into execution_traces (task_id, event_type, content)
                values (?, 'compact', ?)
                """,
                (task_id, f"compacted {len(traces)} events into task state"),
            )
            for trace in recent:
                self.conn.execute(
                    """
                    insert into execution_traces (task_id, event_type, content)
                    values (?, ?, ?)
                    """,
                    (task_id, trace["event_type"], trace["content"]),
                )
            self.conn.commit()
        return {"compacted": len(traces), "kept": len(recent), "summary": summary}

    def _build_compact_summary(self, state: dict[str, Any], traces: list[dict[str, Any]]) -> str:
        files = state.get("files")
        files_text = ", ".join(files) if isinstance(files, list) else "(unknown)"
        parts = [
            f"events={len(traces)}",
            f"status={state.get('status', '(unknown)')}",
            f"test_status={state.get('test_status', '(unknown)')}",
            f"files={files_text}",
        ]
        if state.get("preview_file"):
            parts.append(f"preview_file={state['preview_file']}")
        if state.get("summary"):
            parts.append(f"summary={state['summary']}")
        return "; ".join(parts)
