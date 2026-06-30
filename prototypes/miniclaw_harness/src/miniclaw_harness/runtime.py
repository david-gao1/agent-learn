from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .background import BackgroundTaskManager, TaskWaitingApproval
from .skills import LocalSkillLoader, Skill
from .tools import BashTool, CodeTool, FileTool


class CompletionModel(Protocol):
    def complete(self, instructions: str, prompt: str) -> str:
        ...


class FileListingTool(Protocol):
    def list_files(self, limit: int = 20) -> list[str]:
        ...

    def read_file(self, relative_path: str, max_chars: int = 1200) -> str:
        ...


class CommandTool(Protocol):
    def run(self, command: str) -> str:
        ...


class CodeExecutionTool(Protocol):
    def run(self, code: str) -> dict[str, Any]:
        ...

    def validate(self, code: str) -> None:
        ...


@dataclass(frozen=True)
class ToolDecision:
    action: str
    target: str
    reason: str


@dataclass(frozen=True)
class RepoPlan:
    steps: list[str]
    source: str
    error: str | None = None


@dataclass(frozen=True)
class CodePlan:
    code: str
    source: str
    safety_status: str
    error: str | None = None


class TaskBlockedError(RuntimeError):
    pass


class LocalAgentRuntime:
    def respond(self, message: dict) -> str:
        return (
            "MiniClaw processed message "
            f"#{message['id']} for group {message['group_id']}: {message['content']}"
        )


class ModelBackedRuntime:
    def __init__(self, model: CompletionModel):
        self.model = model

    def respond(self, message: dict) -> str:
        return self.model.complete(
            instructions=(
                "You are the MiniClaw agent runtime inside a local Harness product. "
                "Respond concisely and focus on the user's requested task."
            ),
            prompt=(
                f"Group: {message['group_id']}\n"
                f"User: {message['user_id']}\n"
                f"Message: {message['content']}"
            ),
        )


class SubAgentRuntime:
    def __init__(
        self,
        background: BackgroundTaskManager | None = None,
        workspace: Path | None = None,
        file_tool: FileListingTool | None = None,
        bash_tool: CommandTool | None = None,
        code_tool: CodeExecutionTool | None = None,
        planner: CompletionModel | None = None,
        skill_loader: LocalSkillLoader | None = None,
    ):
        self.background = background
        self.file_tool = file_tool or (FileTool(Path(workspace)) if workspace else None)
        self.bash_tool = bash_tool or (BashTool(Path(workspace)) if workspace else None)
        self.code_tool = code_tool or (CodeTool(Path(workspace)) if workspace else None)
        self.planner = planner
        self.skill_loader = skill_loader
        self.main_context: list[str] = []
        self.child_contexts: list[list[str]] = []
        self.decisions: list[ToolDecision] = []

    def respond(self, message: dict) -> str:
        content = message["content"]
        if "subagent-background:" in content:
            return self._dispatch_background_child(message)

        if "subagent:" not in content:
            response = (
                "MiniClaw processed message "
                f"#{message['id']} for group {message['group_id']}: {content}"
            )
            self.main_context.append(response)
            return response

        task = content.split("subagent:", 1)[1].strip()
        child_context = self._run_child(task)
        self.child_contexts.append(child_context)

        summary = f"SubAgent summary: completed isolated task '{task}'"
        self.main_context.append(summary)
        return summary

    def _run_child(self, task: str) -> list[str]:
        return [
            task,
            "child detail: inspected isolated context",
            "child detail: produced summary only",
        ]

    def resume_background_task(self, task_id: str, task: str) -> None:
        if self.background is None:
            raise RuntimeError("SubAgent background resume requires a background manager")
        decision = self._decide_tool(task)
        if decision.action not in {"analyze_repo", "run_tests"}:
            raise ValueError(f"resume is not supported for action: {decision.action}")
        self.background.store.add_execution_trace(
            task_id=task_id,
            event_type="plan",
            content=f"Resume isolated SubAgent background work for task: {task}",
        )
        self.background.resume_existing(
            task_id,
            lambda active_task_id: self._background_result(active_task_id, task, decision),
            pass_task_id=True,
        )

    def _dispatch_background_child(self, message: dict[str, Any]) -> str:
        if self.background is None:
            raise RuntimeError("SubAgent background dispatch requires a background manager")

        task = message["content"].split("subagent-background:", 1)[1].strip()
        child_context = self._run_child(task)
        self.child_contexts.append(child_context)
        decision = self._decide_tool(task)
        self.decisions.append(decision)

        task_id = self.background.run(
            group_id=message["group_id"],
            command=f"subagent: {task}",
            operation=lambda active_task_id: self._background_result(active_task_id, task, decision),
            start=False,
            pass_task_id=True,
        )
        self.background.store.add_execution_trace(
            task_id=task_id,
            event_type="plan",
            content=f"Plan isolated SubAgent background work for task: {task}",
        )
        self.background.store.add_tool_decision(
            task_id=task_id,
            action=decision.action,
            target=decision.target,
            reason=decision.reason,
        )
        self.background.store.add_execution_trace(
            task_id=task_id,
            event_type="decision",
            content=(
                f"{decision.action}\n"
                f"target: {decision.target}\n"
                f"reason: {decision.reason}"
            ),
        )
        self.background.store.add_execution_trace(
            task_id=task_id,
            event_type="tool_call",
            content=self._tool_call_trace(decision),
        )
        self.background.start(
            task_id,
            lambda active_task_id: self._background_result(active_task_id, task, decision),
            pass_task_id=True,
        )
        deadline = time.time() + 2
        while time.time() < deadline:
            background_task = self.background.get(task_id)
            if background_task["status"] != "running":
                break
            time.sleep(0.01)
        background_task = self.background.get(task_id)
        if background_task["status"] != "running" and background_task["result"]:
            if decision.action != "analyze_repo":
                self.background.store.add_execution_trace(
                    task_id=task_id,
                    event_type="observation",
                    content=self._observation_summary(background_task["result"]),
                )
            self.background.store.add_execution_trace(
                task_id=task_id,
                event_type="final_result",
                content=background_task["result"],
            )

        summary = f"SubAgent background task {task_id}: dispatched isolated task '{task}'"
        self.main_context.append(summary)
        return summary

    def _background_result(self, task_id: str, task: str, decision: ToolDecision) -> str:
        if decision.action == "analyze_repo":
            result = self._run_repo_analysis_task(task_id, task)
        elif decision.action == "run_tests":
            result = self._run_test_task(task_id, task, decision)
        elif decision.action == "codeact":
            result = self._run_codeact_task(task_id, task, decision)
        elif decision.action == "read_file":
            result = self._run_file_read_task(task, decision)
        elif decision.action == "list_files":
            result = self._run_file_list_task(task, decision, include_preview=False)
        else:
            result = self._run_file_list_task(task, decision, include_preview=True, include_bash=True)
        return result

    def _observation_summary(self, result: str) -> str:
        markers = [
            "Test command output:",
            "Observed workspace files:",
            "First file preview",
            "Bash pwd:",
        ]
        for marker in markers:
            if marker in result:
                return result[result.index(marker) :].strip()
        return result

    def _tool_call_trace(self, decision: ToolDecision) -> str:
        if decision.action == "analyze_repo":
            return "FileTool.list_files: workspace"
        if decision.action == "run_tests":
            return f"BashTool.run: {decision.target}"
        if decision.action == "read_file":
            return f"FileTool.read_file: {decision.target}"
        if decision.action == "list_files":
            return f"FileTool.list_files: {decision.target}"
        if decision.action == "codeact":
            return f"CodeTool.run: {decision.target}"
        return f"Inspect workspace: {decision.target}"

    def _trace(self, task_id: str, event_type: str, content: str) -> None:
        if self.background is None:
            return
        self.background.store.add_execution_trace(
            task_id,
            event_type,
            content,
            compact_threshold=20,
            keep_recent=8,
        )

    def _run_repo_analysis_task(self, task_id: str, task: str) -> str:
        if self.file_tool is None or self.bash_tool is None:
            return "Repo analysis summary: workspace tools are unavailable."

        plan = self._plan_repo_analysis(task_id, task)
        skill = self._select_skill(task)
        if skill is not None:
            self._trace(task_id, "skill_load", f"{skill.name}: {self._skill_summary(skill)}")
        recalled_memories = self._recall_repo_memories(task_id, task)
        existing_state = self._load_task_state(task_id)
        files = existing_state.get("files") if isinstance(existing_state.get("files"), list) else None
        preview_file = str(existing_state.get("preview_file", ""))
        preview = str(existing_state.get("preview", ""))
        tools_used: list[str] = []

        if files is not None and preview_file and preview:
            self._trace(
                task_id,
                "observation",
                f"Reused task state: files={', '.join(files)}; preview_file={preview_file}",
            )
        else:
            files = []
            preview = ""
            preview_file = ""
            if "list_files" in plan.steps:
                tools_used.append("FileTool.list_files")
                files = self.file_tool.list_files(limit=20)
                observed = ", ".join(files) if files else "(none)"
                self._trace(task_id, "observation", f"Observed workspace files: {observed}")
            if "read_file" in plan.steps:
                preview_file = files[0] if files else ""
                if preview_file:
                    tools_used.append("FileTool.read_file")
                    self._trace(task_id, "tool_call", f"FileTool.read_file: {preview_file}")
                    preview = self.file_tool.read_file(preview_file, max_chars=400)
                    self._trace(task_id, "observation", f"First file preview ({preview_file}): {preview}")

        test_output = ""
        if "run_tests" in plan.steps:
            tools_used.append("BashTool.run")
            self._trace(task_id, "tool_call", "BashTool.run: python3 -m unittest discover -s tests -v")
            test_output = self.bash_tool.run("python3 -m unittest discover -s tests -v")
            self._trace(task_id, "observation", f"Test command output: {test_output}")
        observed = ", ".join(files) if files else "(none)"
        test_failed = test_output.startswith("exit ")

        summary = (
            "Repo analysis summary: "
            f"files={observed}; "
            f"preview={preview}; "
            f"tests={test_output}"
        )
        self._persist_repo_analysis_state(
            task_id=task_id,
            files=files,
            preview_file=preview_file,
            preview=preview,
            test_output=test_output,
            summary=summary,
            plan_source=plan.source,
            planner_error=plan.error,
            skill=skill,
            recalled_memories=recalled_memories,
            tools_used=tools_used,
        )
        if test_failed:
            raise TaskBlockedError(f"repo analysis blocked by failing tests: {test_output}")
        self._remember_repo_analysis(task_id, task, summary)
        return summary

    def _recall_repo_memories(self, task_id: str, task: str) -> list[dict[str, Any]]:
        if self.background is None:
            return []

        query = "repo" if self._wants_repo_analysis(task) else task
        memories = self.background.store.search_memories(query, limit=3)
        if memories:
            self._trace(
                task_id,
                "memory_recall",
                self._memory_summary(memories),
            )
        return memories

    def _remember_repo_analysis(self, task_id: str, task: str, summary: str) -> None:
        if self.background is None:
            return
        self.background.store.add_memory(
            kind="repo_analysis",
            topic=task,
            content=summary,
            source_task_id=task_id,
        )

    def _memory_summary(self, memories: list[dict[str, Any]]) -> str:
        parts = []
        for memory in memories:
            parts.append(
                f"#{memory['id']} from {memory.get('source_task_id')}: {memory['content'][:160]}"
            )
        return " | ".join(parts)

    def _select_skill(self, task: str) -> Skill | None:
        if self.skill_loader is None:
            return None

        normalized = task.lower()
        for label in self.skill_loader.list_labels():
            name = label["name"]
            description = label.get("description", "")
            if (
                name.lower() in normalized
                or name.replace("-", " ") in normalized
                or self._wants_repo_analysis(task) and "repository" in description.lower()
            ):
                return self.skill_loader.load(name)
        return None

    def _skill_summary(self, skill: Skill) -> str:
        lines = [
            line.strip()
            for line in skill.body.splitlines()
            if line.strip() and not line.startswith("---") and ":" not in line
        ]
        return " ".join(lines[:3])[:240]

    def _plan_repo_analysis(self, task_id: str, task: str) -> RepoPlan:
        fallback = ["list_files", "read_file", "run_tests", "summarize"]
        if self.planner is None:
            return RepoPlan(steps=fallback, source="rule")
        try:
            response = self.planner.complete(
                instructions=(
                    "You are planning MiniClaw repository analysis. "
                    "Only return JSON with a steps array. Allowed steps: "
                    "list_files, read_file, run_tests, summarize."
                ),
                prompt=f"Task id: {task_id}\nTask: {task}",
            )
            parsed = self._parse_plan_response(response)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            return self._fallback_repo_plan(task_id, fallback, f"planner returned invalid JSON: {exc}")

        steps = parsed.get("steps", [])
        allowed = {"list_files", "read_file", "run_tests", "summarize"}
        plan = [step for step in steps if step in allowed]
        if not plan:
            return self._fallback_repo_plan(task_id, fallback, "planner returned no allowed steps")
        self._trace(task_id, "model_plan", " -> ".join(plan))
        return RepoPlan(steps=plan, source="model")

    def _fallback_repo_plan(self, task_id: str, fallback: list[str], error: str) -> RepoPlan:
        self._trace(task_id, "planner_error", error)
        self._trace(task_id, "model_plan", f"fallback: {' -> '.join(fallback)}")
        return RepoPlan(steps=fallback, source="rule_fallback", error=error)

    def _parse_plan_response(self, response: str) -> dict[str, Any]:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            start = response.find("{")
            end = response.rfind("}")
            if start < 0 or end < start:
                raise
            return json.loads(response[start : end + 1])

    def _load_task_state(self, task_id: str) -> dict[str, Any]:
        if self.background is None:
            return {}
        try:
            return self.background.store.get_task_state(task_id)
        except KeyError:
            return {}

    def _persist_repo_analysis_state(
        self,
        task_id: str,
        files: list[str],
        preview_file: str,
        preview: str,
        test_output: str,
        summary: str,
        plan_source: str = "rule",
        planner_error: str | None = None,
        skill: Skill | None = None,
        recalled_memories: list[dict[str, Any]] | None = None,
        tools_used: list[str] | None = None,
    ) -> None:
        if self.background is None:
            return
        recalled_memories = recalled_memories or []
        tools_used = tools_used or []
        self.background.store.set_task_state(
            task_id,
            {
                "kind": "repo_analysis",
                "tools_used": tools_used,
                "files": files,
                "preview_file": preview_file,
                "preview": preview,
                "status": "blocked" if test_output.startswith("exit ") else "completed",
                "test_status": "failed" if test_output.startswith("exit ") else "completed",
                "test_output": test_output,
                "summary": summary,
                "plan_source": plan_source,
                **({"planner_error": planner_error} if planner_error else {}),
                **(
                    {"skill": skill.name, "skill_summary": self._skill_summary(skill)}
                    if skill is not None
                    else {}
                ),
                **(
                    {
                        "memory_count": len(recalled_memories),
                        "memory_summary": self._memory_summary(recalled_memories),
                    }
                    if recalled_memories
                    else {}
                ),
                **(
                    {"blocked_reason": test_output}
                    if test_output.startswith("exit ")
                    else {}
                ),
            },
        )

    def _run_file_list_task(
        self,
        task: str,
        decision: ToolDecision,
        include_preview: bool,
        include_bash: bool = False,
    ) -> str:
        if self.file_tool is None:
            return f"SubAgent background result: completed isolated task '{task}'"

        observed_files = self.file_tool.list_files(limit=20)
        observed = ", ".join(observed_files) if observed_files else "(none)"
        preview = ""
        if include_preview and observed_files:
            preview = (
                f" First file preview ({observed_files[0]}): "
                f"{self.file_tool.read_file(observed_files[0], max_chars=400)}"
            )
        bash_output = ""
        if include_bash and self.bash_tool is not None:
            bash_output = f" Bash pwd: {self.bash_tool.run('pwd')}"
        return (
            f"SubAgent background result: completed isolated task '{task}'. "
            f"Decision: {decision.action} {decision.target} because {decision.reason}. "
            f"Observed workspace files: {observed}.{preview}{bash_output}"
        )

    def _run_file_read_task(self, task: str, decision: ToolDecision) -> str:
        return self._run_file_list_task(task, decision, include_preview=True, include_bash=False)

    def _run_test_task(self, task_id: str, task: str, decision: ToolDecision) -> str:
        if self.bash_tool is None:
            return f"SubAgent background result: completed isolated task '{task}'"
        if self._needs_approval(task) and not self._is_approved(task_id):
            self._request_approval(task_id, task, decision)
            raise TaskWaitingApproval(f"waiting for approval: {decision.action} {decision.target}")
        output = self.bash_tool.run("python3 -m unittest discover -s tests -v")
        return (
            f"SubAgent background result: completed isolated task '{task}'. "
            f"Decision: {decision.action} {decision.target} because {decision.reason}. "
            f"Test command output: {output}"
        )

    def _run_codeact_task(self, task_id: str, task: str, decision: ToolDecision) -> str:
        if self.code_tool is None:
            return f"SubAgent background result: completed isolated task '{task}'"
        plan = self._plan_codeact(task_id, task)
        code = plan.code
        self._trace(task_id, "codeact", f"CodeTool.run: {code}")
        result = self.code_tool.run(code)
        result_text = json.dumps(result, ensure_ascii=False, sort_keys=True)
        self._trace(task_id, "observation", f"CodeAct output: {result_text}")
        if self.background is not None:
            self.background.store.set_task_state(
                task_id,
                {
                    "kind": "codeact",
                    "status": "completed",
                    "code": code,
                    "code_source": plan.source,
                    "code_safety_status": plan.safety_status,
                    **({"code_error": plan.error} if plan.error else {}),
                    "result": result.get("result"),
                    "stdout": result.get("stdout", ""),
                },
            )
        return (
            f"SubAgent background result: completed isolated task '{task}'. "
            f"Decision: {decision.action} {decision.target} because {decision.reason}. "
            f"CodeAct output: {result_text}"
        )

    def _plan_codeact(self, task_id: str, task: str) -> CodePlan:
        fallback = self._rule_code_for_task(task)
        if self.planner is None:
            return CodePlan(code=fallback, source="rule", safety_status="trusted_rule")

        code = self.planner.complete(
            instructions=(
                "Generate restricted Python for MiniClaw CodeAct. "
                "Return code only. Allowed helpers: list_files(), len(), print(), sorted(), str(). "
                "Set a variable named result."
            ),
            prompt=f"Task id: {task_id}\nTask: {task}",
        )
        self._trace(task_id, "model_code", code)
        try:
            self.code_tool.validate(code)
        except ValueError as exc:
            error = f"model code rejected by Harness: {exc}"
            self._trace(task_id, "code_error", error)
            return CodePlan(
                code=fallback,
                source="rule_fallback",
                safety_status="rejected_fallback",
                error=error,
            )
        return CodePlan(code=code, source="model", safety_status="accepted")

    def _rule_code_for_task(self, task: str) -> str:
        normalized = task.lower()
        if "count" in normalized and "file" in normalized:
            return "files = list_files()\nresult = len(files)\nprint(result)"
        return "result = 0\nprint(result)"

    def _needs_approval(self, task: str) -> bool:
        normalized = task.lower()
        return "requires approval" in normalized or "approval" in normalized or "需要审批" in task

    def _is_approved(self, task_id: str) -> bool:
        if self.background is None:
            return False
        try:
            return self.background.store.get_approval(task_id)["status"] == "approved"
        except KeyError:
            return False

    def _request_approval(self, task_id: str, task: str, decision: ToolDecision) -> None:
        if self.background is None:
            return
        reason = f"Human approval required before executing task: {task}"
        self.background.store.request_approval(task_id, decision.action, decision.target, reason)
        self.background.store.set_task_state(
            task_id,
            {
                "kind": "approval_gate",
                "status": "waiting_approval",
                "approval_status": "pending",
                "action": decision.action,
                "target": decision.target,
                "reason": reason,
            },
        )
        self._trace(task_id, "approval_request", reason)

    def _decide_tool(self, task: str) -> ToolDecision:
        if self._wants_repo_analysis(task):
            return ToolDecision(
                action="analyze_repo",
                target="workspace",
                reason="task asks for multi-step repository analysis",
            )
        if self._wants_codeact(task):
            return ToolDecision(
                action="codeact",
                target="restricted python",
                reason="task asks to solve through generated code",
            )
        if self._wants_tests(task):
            return ToolDecision(
                action="run_tests",
                target="python3 -m unittest discover -s tests -v",
                reason="task asks to run tests",
            )
        if self._wants_file_read(task):
            return ToolDecision(
                action="read_file",
                target="first observed file",
                reason="task asks to read file content",
            )
        if self._wants_file_list(task):
            return ToolDecision(
                action="list_files",
                target="workspace",
                reason="task asks to list or summarize structure",
            )
        return ToolDecision(
            action="inspect_workspace",
            target="workspace",
            reason="default workspace inspection",
        )

    def _wants_tests(self, task: str) -> bool:
        normalized = task.lower()
        return "run tests" in normalized or "test" in normalized or "运行测试" in task

    def _wants_codeact(self, task: str) -> bool:
        normalized = task.lower()
        return "codeact" in normalized or "code act" in normalized or "代码执行" in task

    def _wants_file_read(self, task: str) -> bool:
        normalized = task.lower()
        return "read" in normalized or "读取" in task

    def _wants_file_list(self, task: str) -> bool:
        normalized = task.lower()
        return "list" in normalized or "列出" in task or "结构" in task

    def _wants_repo_analysis(self, task: str) -> bool:
        normalized = task.lower()
        return "analyze repo" in normalized or "分析仓库" in task or "分析这个仓库" in task
