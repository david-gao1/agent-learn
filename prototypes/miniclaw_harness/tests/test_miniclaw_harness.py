import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from miniclaw_harness import MiniClawApp, ModelBackedRuntime  # noqa: E402


class RecordingModel:
    def __init__(self):
        self.calls = []

    def complete(self, instructions: str, prompt: str) -> str:
        self.calls.append({"instructions": instructions, "prompt": prompt})
        return "模型回复：已识别 MiniClaw Harness 任务"


class MiniClawHarnessTest(unittest.TestCase):
    def test_processes_local_message_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db")

            message_id = app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="分析这个仓库，并给出 Harness 组件清单",
            )
            app.orchestrator.run_once()

            inbound = app.store.get_message(message_id)
            outbound = app.store.list_outbound(group_id="learning")

            self.assertEqual(inbound["status"], "processed")
            self.assertEqual(len(outbound), 1)
            self.assertIn("MiniClaw", outbound[0]["content"])
            self.assertIn("分析这个仓库", outbound[0]["content"])

    def test_scheduler_turns_due_task_into_normal_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db")

            task_id = app.scheduler.schedule_once(
                group_id="ops",
                user_id="system",
                content="提醒我检查后台任务",
                run_at=0,
            )
            due_messages = app.scheduler.tick(now=1)
            app.orchestrator.run_once()

            task = app.store.get_task(task_id)
            outbound = app.store.list_outbound(group_id="ops")

            self.assertEqual(task["status"], "dispatched")
            self.assertEqual(len(due_messages), 1)
            self.assertEqual(outbound[0]["source_message_id"], due_messages[0])
            self.assertIn("提醒我检查后台任务", outbound[0]["content"])

    def test_orchestrator_can_use_model_backed_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = RecordingModel()
            app = MiniClawApp.open(
                Path(tmp) / "miniclaw.db",
                runtime=ModelBackedRuntime(model),
            )

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="用真实模型解释 Agent Loop",
            )
            app.orchestrator.run_once()

            outbound = app.store.list_outbound(group_id="learning")
            self.assertEqual(outbound[0]["content"], "模型回复：已识别 MiniClaw Harness 任务")
            self.assertIn("用真实模型解释 Agent Loop", model.calls[0]["prompt"])
            self.assertIn("MiniClaw", model.calls[0]["instructions"])


if __name__ == "__main__":
    unittest.main()
