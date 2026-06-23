from pathlib import Path

from .context import compact_messages
from .skills import LocalSkillLoader
from .tasks import TaskStore
from .tools import run_bash


class HarnessAgent:
    def __init__(
        self,
        workspace: Path,
        skill_loader: LocalSkillLoader,
        task_store: TaskStore,
        max_context_messages: int = 6,
    ):
        self.workspace = Path(workspace)
        self.skill_loader = skill_loader
        self.task_store = task_store
        self.max_context_messages = max_context_messages
        self.messages: list[str] = []

    def run(self, user_request: str) -> str:
        task_id = self.task_store.add(user_request)
        self._remember(f"User request: {user_request}")

        skill_name = self._select_skill(user_request)
        if skill_name:
            skill = self.skill_loader.load(skill_name)
            self._remember(f"Loaded skill: {skill.name}")
        else:
            self._remember("Loaded skill: none")

        files = run_bash(
            "find . -path './.demo_state' -prune -o -path '*/__pycache__' -prune -o -type f -print | sort",
            cwd=self.workspace,
        )
        self._remember(f"Workspace files: {files}")
        self.task_store.update(task_id, "done")
        self._remember("Task status: done")

        return "\n".join(
            [
                self.messages[-3],
                self.messages[-2],
                self.messages[-1],
                f"Context messages: {len(self.messages)}",
            ]
        )

    def _select_skill(self, user_request: str) -> str | None:
        request = user_request.lower()
        for label in self.skill_loader.list_labels():
            name = label["name"]
            if name.lower() in request or name.replace("-", " ") in request:
                return name
        return None

    def _remember(self, message: str) -> None:
        self.messages.append(message)
        self.messages = compact_messages(self.messages, keep_last=self.max_context_messages)
