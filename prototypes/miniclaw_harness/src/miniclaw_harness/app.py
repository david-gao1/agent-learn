from __future__ import annotations

from pathlib import Path

from .background import BackgroundTaskManager
from .channel import LocalChannel
from .ipc import FileSystemIPC
from .orchestrator import Orchestrator
from .queue import GroupQueue
from .router import OutputRouter
from .runtime import LocalAgentRuntime, SubAgentRuntime
from .scheduler import OneShotScheduler
from .store import MiniClawStore


class MiniClawApp:
    def __init__(
        self,
        store: MiniClawStore,
        runtime: LocalAgentRuntime | None = None,
        ipc_root: Path | None = None,
    ):
        self.store = store
        self.channel = LocalChannel(store)
        self.queue = GroupQueue()
        self.runtime = runtime or LocalAgentRuntime()
        self.router = OutputRouter(store)
        self.scheduler = OneShotScheduler(store)
        self.background = BackgroundTaskManager(store)
        if isinstance(self.runtime, SubAgentRuntime) and self.runtime.background is None:
            self.runtime.background = self.background
        self.ipc = FileSystemIPC(
            root=ipc_root or store.db_path.parent / "ipc",
            store=store,
            scheduler=self.scheduler,
        )
        self.orchestrator = Orchestrator(
            store=store,
            queue=self.queue,
            runtime=self.runtime,
            router=self.router,
        )

    @classmethod
    def open(
        cls,
        db_path: Path,
        runtime: LocalAgentRuntime | None = None,
        ipc_root: Path | None = None,
    ) -> "MiniClawApp":
        return cls(MiniClawStore(db_path), runtime=runtime, ipc_root=ipc_root)
