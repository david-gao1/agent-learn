import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT.parent / "minimal_harness_agent" / "src"))

from miniclaw_harness import FileSystemIPC, MiniClawApp, ModelBackedRuntime  # noqa: E402
from minimal_harness_agent import OpenAIResponsesModel  # noqa: E402


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

    @unittest.skipUnless(
        os.environ.get("RUN_REAL_MODEL_TESTS") == "1" and os.environ.get("OPENAI_API_KEY"),
        "Set RUN_REAL_MODEL_TESTS=1 and OPENAI_API_KEY to call a real model",
    )
    def test_miniclaw_real_model_smoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = MiniClawApp.open(
                Path(tmp) / "miniclaw.db",
                runtime=ModelBackedRuntime(OpenAIResponsesModel.from_env()),
            )

            app.channel.send(
                group_id="real-model",
                user_id="user-1",
                content="用一句话解释 MiniClaw 的 Harness 作用",
            )
            app.orchestrator.run_once()

            outbound = app.store.list_outbound(group_id="real-model")
            self.assertTrue(outbound[0]["content"].strip())

    def test_filesystem_ipc_drains_input_and_writes_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            app = MiniClawApp.open(tmp_path / "miniclaw.db", ipc_root=tmp_path / "ipc")

            app.ipc.write_input(
                group_id="learning",
                user_id="ipc-user",
                content="通过 IPC 分析 Harness",
            )
            drained_messages = app.ipc.drain_inputs()
            app.orchestrator.run_once()
            written = app.ipc.flush_outbound(group_id="learning")

            namespace = tmp_path / "ipc" / "learning"
            self.assertTrue((namespace / "input").is_dir())
            self.assertTrue((namespace / "messages").is_dir())
            self.assertTrue((namespace / "tasks").is_dir())
            self.assertEqual(len(drained_messages), 1)
            self.assertEqual(len(written), 1)
            self.assertIn("通过 IPC 分析 Harness", written[0].read_text(encoding="utf-8"))

    def test_filesystem_ipc_drains_task_files_into_scheduler(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            app = MiniClawApp.open(tmp_path / "miniclaw.db", ipc_root=tmp_path / "ipc")

            app.ipc.write_task(
                group_id="ops",
                user_id="ipc-system",
                content="IPC 定时提醒",
                run_at=0,
            )
            task_ids = app.ipc.drain_tasks()
            due_messages = app.scheduler.tick(now=1)
            app.orchestrator.run_once()

            task = app.store.get_task(task_ids[0])
            outbound = app.store.list_outbound(group_id="ops")
            self.assertEqual(task["status"], "dispatched")
            self.assertEqual(len(due_messages), 1)
            self.assertIn("IPC 定时提醒", outbound[0]["content"])


if __name__ == "__main__":
    unittest.main()
