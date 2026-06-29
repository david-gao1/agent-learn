from __future__ import annotations

from .queue import GroupQueue
from .router import OutputRouter
from .runtime import LocalAgentRuntime
from .store import MiniClawStore


class Orchestrator:
    def __init__(
        self,
        store: MiniClawStore,
        queue: GroupQueue,
        runtime: LocalAgentRuntime,
        router: OutputRouter,
    ):
        self.store = store
        self.queue = queue
        self.runtime = runtime
        self.router = router

    def run_once(self) -> int | None:
        message = self.store.next_pending_message()
        if not message:
            return None

        group_id = message["group_id"]
        if not self.queue.begin(group_id):
            return None

        try:
            self.store.update_message_status(message["id"], "processing")
            response = self.runtime.respond(message)
            self.router.route(
                group_id=group_id,
                content=response,
                source_message_id=message["id"],
            )
            self.store.update_message_status(message["id"], "processed")
            return message["id"]
        finally:
            self.queue.finish(group_id)
