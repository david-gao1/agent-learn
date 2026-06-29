from __future__ import annotations

import argparse
import time
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent
import sys

sys.path.insert(0, str(ROOT / "src"))

from miniclaw_harness import MiniClawApp, SubAgentRuntime  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MiniClaw local Harness prototype")
    parser.add_argument("--db", default=str(ROOT / ".miniclaw" / "miniclaw.db"))
    parser.add_argument("--runtime", choices=["local", "subagent"], default="local")
    subcommands = parser.add_subparsers(dest="command", required=True)

    send = subcommands.add_parser("send")
    send.add_argument("content")
    send.add_argument("--group", default="default")
    send.add_argument("--user", default="local-user")

    schedule = subcommands.add_parser("schedule")
    schedule.add_argument("content")
    schedule.add_argument("--group", default="default")
    schedule.add_argument("--user", default="system")
    schedule.add_argument("--delay", type=float, default=0)

    subcommands.add_parser("tick")
    subcommands.add_parser("run-once")
    subcommands.add_parser("outbox")

    ipc_send = subcommands.add_parser("ipc-send")
    ipc_send.add_argument("content")
    ipc_send.add_argument("--group", default="default")
    ipc_send.add_argument("--user", default="ipc-user")

    ipc_task = subcommands.add_parser("ipc-task")
    ipc_task.add_argument("content")
    ipc_task.add_argument("--group", default="default")
    ipc_task.add_argument("--user", default="ipc-system")
    ipc_task.add_argument("--run-at", type=float, default=0)

    subcommands.add_parser("ipc-drain")

    ipc_flush = subcommands.add_parser("ipc-flush")
    ipc_flush.add_argument("--group", default="default")

    background_run = subcommands.add_parser("background-run")
    background_run.add_argument("command_text")
    background_run.add_argument("--group", default="default")

    subcommands.add_parser("background-list")

    background_show = subcommands.add_parser("background-show")
    background_show.add_argument("task_id")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    runtime = SubAgentRuntime() if args.runtime == "subagent" else None
    app = MiniClawApp.open(Path(args.db), runtime=runtime)

    if args.command == "send":
        message_id = app.channel.send(args.group, args.user, args.content)
        print(f"queued message {message_id}")
    elif args.command == "schedule":
        task_id = app.scheduler.schedule_once(
            args.group,
            args.user,
            args.content,
            run_at=time.time() + args.delay,
        )
        print(f"scheduled task {task_id}")
    elif args.command == "tick":
        created = app.scheduler.tick(time.time())
        print(f"created messages {created}")
    elif args.command == "run-once":
        print(f"processed message {app.orchestrator.run_once()}")
    elif args.command == "outbox":
        for row in app.store.list_outbound(group_id="default"):
            print(f"#{row['id']} from {row['source_message_id']}: {row['content']}")
    elif args.command == "ipc-send":
        path = app.ipc.write_input(args.group, args.user, args.content)
        print(f"wrote ipc input {path}")
    elif args.command == "ipc-task":
        path = app.ipc.write_task(args.group, args.user, args.content, args.run_at)
        print(f"wrote ipc task {path}")
    elif args.command == "ipc-drain":
        message_ids = app.ipc.drain_inputs()
        task_ids = app.ipc.drain_tasks()
        print(f"drained messages {message_ids}; tasks {task_ids}")
    elif args.command == "ipc-flush":
        paths = app.ipc.flush_outbound(args.group)
        print(f"flushed outbound {[str(path) for path in paths]}")
    elif args.command == "background-run":
        task_id = app.background.run(
            group_id=args.group,
            command=args.command_text,
            operation=lambda: f"CLI background task completed: {args.command_text}",
        )
        deadline = time.time() + 2
        while time.time() < deadline:
            task = app.background.get(task_id)
            if task["status"] != "running":
                break
            time.sleep(0.01)
        print(f"started background task {task_id}")
    elif args.command == "background-list":
        for task in app.background.list():
            print(
                f"#{task['id']} group={task['group_id']} "
                f"status={task['status']}: {task['command']}"
            )
    elif args.command == "background-show":
        task = app.background.get(args.task_id)
        print(
            f"#{task['id']} group={task['group_id']} status={task['status']}\n"
            f"command: {task['command']}\n"
            f"result: {task['result']}"
        )


if __name__ == "__main__":
    main()
