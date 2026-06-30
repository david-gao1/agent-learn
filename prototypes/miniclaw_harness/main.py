from __future__ import annotations

import argparse
import json
import time
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent
import sys

sys.path.insert(0, str(ROOT / "src"))

from miniclaw_harness import LocalSkillLoader, MiniClawApp, SubAgentRuntime  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MiniClaw local Harness prototype")
    parser.add_argument("--db", default=str(ROOT / ".miniclaw" / "miniclaw.db"))
    parser.add_argument("--runtime", choices=["local", "subagent"], default="local")
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--skills-root", default=None)
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

    task_report = subcommands.add_parser("task-report")
    task_report.add_argument("task_id")

    trace_show = subcommands.add_parser("trace-show")
    trace_show.add_argument("task_id")

    state_show = subcommands.add_parser("state-show")
    state_show.add_argument("task_id")

    resume_task = subcommands.add_parser("resume-task")
    resume_task.add_argument("task_id")

    approve_task = subcommands.add_parser("approve-task")
    approve_task.add_argument("task_id")

    compact_task = subcommands.add_parser("compact-task")
    compact_task.add_argument("task_id")
    compact_task.add_argument("--keep-recent", type=int, default=5)

    memory_list = subcommands.add_parser("memory-list")
    memory_list.add_argument("query")
    memory_list.add_argument("--limit", type=int, default=5)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    skill_loader = LocalSkillLoader(Path(args.skills_root)) if args.skills_root else None
    runtime = (
        SubAgentRuntime(
            workspace=Path(args.workspace) if args.workspace else None,
            skill_loader=skill_loader,
        )
        if args.runtime == "subagent"
        else None
    )
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
            next_step = _background_next_step(app, task)
            print(
                f"#{task['id']} group={task['group_id']} "
                f"status={task['status']}: {task['command']}"
                f"{next_step}"
            )
    elif args.command == "background-show":
        task = app.background.get(args.task_id)
        print(
            f"#{task['id']} group={task['group_id']} status={task['status']}\n"
            f"command: {task['command']}\n"
            f"result: {task['result']}"
        )
    elif args.command == "task-report":
        print(build_task_report(app, args.task_id))
    elif args.command == "trace-show":
        traces = app.store.list_execution_traces(args.task_id)
        for trace in traces:
            print(f"{trace['event_type']}: {trace['content']}")
        try:
            decision = app.store.get_tool_decision(args.task_id)
            print(f"decision_summary: {decision['action']}")
            print(f"target: {decision['target']}")
            print(f"reason: {decision['reason']}")
        except KeyError:
            print("decision_summary: (none)")
    elif args.command == "state-show":
        try:
            state = app.store.get_task_state(args.task_id)
        except KeyError:
            print("state: (none)")
            return
        for key in sorted(state):
            value = state[key]
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            elif isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False, sort_keys=True)
            print(f"{key}: {value}")
    elif args.command == "resume-task":
        if not isinstance(app.runtime, SubAgentRuntime):
            raise RuntimeError("resume-task requires --runtime subagent")
        task = app.background.get(args.task_id)
        if not task["command"].startswith("subagent: "):
            raise ValueError(f"cannot resume non-subagent task: {task['command']}")
        app.runtime.resume_background_task(args.task_id, task["command"].split("subagent: ", 1)[1])
        deadline = time.time() + 2
        while time.time() < deadline:
            current = app.background.get(args.task_id)
            if current["status"] != "running":
                break
            time.sleep(0.01)
        print(f"resumed background task {args.task_id}")
    elif args.command == "approve-task":
        if not isinstance(app.runtime, SubAgentRuntime):
            raise RuntimeError("approve-task requires --runtime subagent")
        task = app.background.get(args.task_id)
        if not task["command"].startswith("subagent: "):
            raise ValueError(f"cannot approve non-subagent task: {task['command']}")
        app.store.approve_task(args.task_id)
        app.store.add_execution_trace(args.task_id, "approval", "approved")
        app.runtime.resume_background_task(args.task_id, task["command"].split("subagent: ", 1)[1])
        deadline = time.time() + 2
        while time.time() < deadline:
            current = app.background.get(args.task_id)
            if current["status"] != "running":
                break
            time.sleep(0.01)
        current = app.background.get(args.task_id)
        if current["result"]:
            result = current["result"]
            if "Test command output:" in result:
                app.store.add_execution_trace(
                    args.task_id,
                    "observation",
                    result[result.index("Test command output:") :],
                )
            app.store.add_execution_trace(args.task_id, "final_result", result)
        print(f"approved background task {args.task_id}")
    elif args.command == "compact-task":
        result = app.store.compact_task_trace(args.task_id, keep_recent=args.keep_recent)
        print(
            f"compacted task {args.task_id}: "
            f"compacted={result['compacted']} kept={result['kept']}"
        )
    elif args.command == "memory-list":
        for memory in app.store.search_memories(args.query, limit=args.limit):
            state_summary = _memory_source_state_summary(app, memory)
            print(
                f"#{memory['id']} kind={memory['kind']} "
                f"source={memory['source_task_id']}: {memory['content']}"
                f"{state_summary}"
            )


def build_task_report(app: MiniClawApp, task_id: str) -> str:
    task = app.background.get(task_id)
    lines = [
        f"# MiniClaw Task Report: {task_id}",
        "",
        "## Task",
        "",
        f"- group: {task['group_id']}",
        f"- status: {task['status']}",
        f"- command: {task['command']}",
        f"- result: {task['result']}",
        "",
        "## Tool Decision",
        "",
    ]

    try:
        decision = app.store.get_tool_decision(task_id)
    except KeyError:
        lines.append("- (none)")
    else:
        lines.extend(
            [
                f"- action: {decision['action']}",
                f"- target: {decision['target']}",
                f"- reason: {decision['reason']}",
            ]
        )

    lines.extend(["", "## Trace", ""])
    traces = app.store.list_execution_traces(task_id)
    if traces:
        for trace in traces:
            lines.append(f"- {trace['event_type']}: {trace['content']}")
    else:
        lines.append("- (none)")

    lines.extend(["", "## State", ""])
    try:
        state = app.store.get_task_state(task_id)
    except KeyError:
        lines.append("- (none)")
    else:
        for key in sorted(state):
            value = state[key]
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            elif isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False, sort_keys=True)
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## State Field Notes", ""])
        lines.extend(_state_field_notes(state))

    lines.extend(["", "## Approval", ""])
    try:
        approval = app.store.get_approval(task_id)
    except KeyError:
        lines.append("- (none)")
    else:
        for key in ["status", "action", "target", "reason"]:
            lines.append(f"- {key}: {approval[key]}")

    return "\n".join(str(line) for line in lines)


def _state_field_notes(state: dict) -> list[str]:
    explanations = {
        "tools_used": "shows which Harness tool boundaries this task crossed.",
        "last_observation_at": "connects recoverable state back to the latest environment observation.",
        "code_safety_status": (
            "records whether CodeAct code was trusted rule code, "
            "accepted model code, or rejected model code fallback."
        ),
        "compact_summary": "keeps a durable summary when long trace history is compacted.",
        "memory_summary": "shows which long-term memories were recalled before this task continued.",
    }
    notes = [
        f"- {key}: {explanations[key]}"
        for key in sorted(explanations)
        if key in state
    ]
    return notes or ["- (none)"]


def _memory_source_state_summary(app: MiniClawApp, memory: dict) -> str:
    source_task_id = memory.get("source_task_id")
    if not source_task_id:
        return ""
    try:
        state = app.store.get_task_state(source_task_id)
    except KeyError:
        return ""
    parts = [
        f"status={state.get('status', '(unknown)')}",
        f"test_status={state.get('test_status', '(unknown)')}",
    ]
    tools_used = state.get("tools_used")
    if isinstance(tools_used, list) and tools_used:
        parts.append(f"tools_used={', '.join(str(tool) for tool in tools_used)}")
    if state.get("last_observation_at") is not None:
        parts.append(f"last_observation_at={state['last_observation_at']}")
    return f" | state: {'; '.join(parts)}"


def _background_next_step(app: MiniClawApp, task: dict) -> str:
    task_id = task["id"]
    if task["status"] == "waiting_approval":
        return f" next_step=approve-task {task_id}"
    try:
        state = app.store.get_task_state(task_id)
    except KeyError:
        return ""
    if state.get("status") == "blocked":
        return f" next_step=resume-task {task_id}"
    return ""


if __name__ == "__main__":
    main()
