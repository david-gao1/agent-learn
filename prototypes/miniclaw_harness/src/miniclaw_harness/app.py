from __future__ import annotations

from pathlib import Path

from .channel import LocalChannel
from .orchestrator import Orchestrator
from .queue import GroupQueue
from .router import OutputRouter
from .runtime import LocalAgentRuntime
from .scheduler import OneShotScheduler
from .store import MiniClawStore


class MiniClawApp:
    def __init__(self, store: MiniClawStore, runtime: LocalAgentRuntime | None = None):
        self.store = store
        self.channel = LocalChannel(store)
        self.queue = GroupQueue()
        self.runtime = runtime or LocalAgentRuntime()
        self.router = OutputRouter(store)
        self.scheduler = OneShotScheduler(store)
        self.orchestrator = Orchestrator(
            store=store,
            queue=self.queue,
            runtime=self.runtime,
            router=self.router,
        )

    @classmethod
    def open(cls, db_path: Path, runtime: LocalAgentRuntime | None = None) -> "MiniClawApp":
        return cls(MiniClawStore(db_path), runtime=runtime)
