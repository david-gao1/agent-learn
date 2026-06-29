import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT.parent / "minimal_harness_agent" / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from miniclaw_harness import (  # noqa: E402
    BackgroundTaskManager,
    BashTool,
    FileTool,
    FileSystemIPC,
    MiniClawApp,
    ModelBackedRuntime,
    SubAgentRuntime,
)
from minimal_harness_agent import OpenAIResponsesModel  # noqa: E402
from main import main as miniclaw_cli  # noqa: E402


class RecordingModel:
    def __init__(self):
        self.calls = []

    def complete(self, instructions: str, prompt: str) -> str:
        self.calls.append({"instructions": instructions, "prompt": prompt})
        return "模型回复：已识别 MiniClaw Harness 任务"


class RecordingFileTool:
    def __init__(self):
        self.calls = 0
        self.reads = []

    def list_files(self, limit: int = 20) -> list[str]:
        self.calls += 1
        return ["observed.py"]

    def read_file(self, relative_path: str, max_chars: int = 1200) -> str:
        self.reads.append((relative_path, max_chars))
        return "fake observed content"


class RecordingBashTool:
    def __init__(self):
        self.commands = []

    def run(self, command: str) -> str:
        self.commands.append(command)
        return "fake bash output"


class MiniClawHarnessTest(unittest.TestCase):
    def run_cli(self, *args: str) -> str:
        output = StringIO()
        with redirect_stdout(output):
            miniclaw_cli(list(args))
        return output.getvalue()

    def test_file_tool_lists_workspace_files_with_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            (workspace / ".git").mkdir(parents=True)
            (workspace / "src").mkdir()
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            (workspace / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
            (workspace / ".git" / "config").write_text("hidden\n", encoding="utf-8")

            files = FileTool(workspace).list_files(limit=10)

            self.assertEqual(files, ["README.md", "src/app.py"])

    def test_file_tool_reads_workspace_file_with_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "README.md").write_text("abcdef", encoding="utf-8")

            content = FileTool(workspace).read_file("README.md", max_chars=3)

            self.assertEqual(content, "abc")

    def test_file_tool_blocks_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workspace = tmp_path / "workspace"
            workspace.mkdir()
            (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")

            with self.assertRaises(ValueError):
                FileTool(workspace).read_file("../secret.txt")

    def test_bash_tool_runs_allowlisted_commands_in_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")

            output = BashTool(workspace).run("ls")

            self.assertIn("README.md", output)

    def test_bash_tool_blocks_unapproved_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()

            with self.assertRaises(ValueError):
                BashTool(workspace).run("rm -rf .")

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

    def test_subagent_runtime_keeps_child_context_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = SubAgentRuntime()
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db", runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent: 阅读测试目录并总结风险",
            )
            app.orchestrator.run_once()

            outbound = app.store.list_outbound(group_id="learning")
            self.assertIn("SubAgent summary", outbound[0]["content"])
            self.assertIn("阅读测试目录并总结风险", runtime.child_contexts[0][0])
            self.assertNotIn("child detail", runtime.main_context[0])
            self.assertIn("SubAgent summary", runtime.main_context[0])

    def test_subagent_runtime_can_dispatch_isolated_background_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = SubAgentRuntime()
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db", runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: 汇总代码仓库结构",
            )
            app.orchestrator.run_once()

            outbound = app.store.list_outbound(group_id="learning")
            tasks = app.background.list()

            self.assertIn("SubAgent background task", outbound[0]["content"])
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0]["status"], "completed")
            self.assertIn("汇总代码仓库结构", tasks[0]["command"])
            self.assertIn("SubAgent background result", tasks[0]["result"])
            self.assertIn("汇总代码仓库结构", runtime.child_contexts[0][0])
            self.assertNotIn("child detail", runtime.main_context[0])

    def test_subagent_background_work_can_observe_workspace_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workspace = tmp_path / "workspace"
            (workspace / "src").mkdir(parents=True)
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            (workspace / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
            runtime = SubAgentRuntime(workspace=workspace)
            app = MiniClawApp.open(tmp_path / "miniclaw.db", runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: inspect workspace files",
            )
            app.orchestrator.run_once()

            task = app.background.list()[0]

            self.assertEqual(task["status"], "completed")
            self.assertIn("README.md", task["result"])
            self.assertIn("src/app.py", task["result"])
            self.assertIn("workspace files", runtime.child_contexts[0][0])
            self.assertNotIn("README.md", runtime.main_context[0])

    def test_subagent_background_work_observes_workspace_through_file_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_tool = RecordingFileTool()
            runtime = SubAgentRuntime(file_tool=file_tool)
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db", runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: inspect through tool",
            )
            app.orchestrator.run_once()

            task = app.background.list()[0]

            self.assertEqual(file_tool.calls, 1)
            self.assertIn("observed.py", task["result"])

    def test_subagent_background_work_reads_observed_file_through_file_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_tool = RecordingFileTool()
            runtime = SubAgentRuntime(file_tool=file_tool)
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db", runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: inspect through read tool",
            )
            app.orchestrator.run_once()

            task = app.background.list()[0]

            self.assertEqual(file_tool.reads, [("observed.py", 400)])
            self.assertIn("fake observed content", task["result"])

    def test_subagent_background_work_runs_bash_through_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_tool = RecordingFileTool()
            bash_tool = RecordingBashTool()
            runtime = SubAgentRuntime(file_tool=file_tool, bash_tool=bash_tool)
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db", runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: inspect with bash",
            )
            app.orchestrator.run_once()

            task = app.background.list()[0]

            self.assertEqual(bash_tool.commands, ["pwd"])
            self.assertIn("fake bash output", task["result"])

    def test_subagent_routes_list_task_to_file_listing_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_tool = RecordingFileTool()
            bash_tool = RecordingBashTool()
            runtime = SubAgentRuntime(file_tool=file_tool, bash_tool=bash_tool)
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db", runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: list files",
            )
            app.orchestrator.run_once()

            self.assertEqual(file_tool.calls, 1)
            self.assertEqual(file_tool.reads, [])
            self.assertEqual(bash_tool.commands, [])
            self.assertEqual(runtime.decisions[-1].action, "list_files")
            self.assertEqual(runtime.decisions[-1].target, "workspace")
            self.assertIn("list", runtime.decisions[-1].reason)

    def test_subagent_routes_read_task_to_file_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_tool = RecordingFileTool()
            bash_tool = RecordingBashTool()
            runtime = SubAgentRuntime(file_tool=file_tool, bash_tool=bash_tool)
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db", runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: read README",
            )
            app.orchestrator.run_once()

            self.assertEqual(file_tool.calls, 1)
            self.assertEqual(file_tool.reads, [("observed.py", 400)])
            self.assertEqual(bash_tool.commands, [])
            self.assertEqual(runtime.decisions[-1].action, "read_file")
            self.assertEqual(runtime.decisions[-1].target, "first observed file")
            self.assertIn("read", runtime.decisions[-1].reason)

    def test_subagent_routes_test_task_to_bash(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_tool = RecordingFileTool()
            bash_tool = RecordingBashTool()
            runtime = SubAgentRuntime(file_tool=file_tool, bash_tool=bash_tool)
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db", runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: run tests",
            )
            app.orchestrator.run_once()

            self.assertEqual(file_tool.calls, 0)
            self.assertEqual(file_tool.reads, [])
            self.assertEqual(bash_tool.commands, ["python3 -m unittest discover -s tests -v"])
            self.assertEqual(runtime.decisions[-1].action, "run_tests")
            self.assertEqual(runtime.decisions[-1].target, "python3 -m unittest discover -s tests -v")
            self.assertIn("test", runtime.decisions[-1].reason)

    def test_subagent_tool_decision_persists_with_background_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "miniclaw.db"
            file_tool = RecordingFileTool()
            bash_tool = RecordingBashTool()
            runtime = SubAgentRuntime(file_tool=file_tool, bash_tool=bash_tool)
            app = MiniClawApp.open(db_path, runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: run tests",
            )
            app.orchestrator.run_once()

            task_id = app.background.list()[0]["id"]
            decision = app.store.get_tool_decision(task_id)
            reopened = MiniClawApp.open(db_path)
            persisted = reopened.store.get_tool_decision(task_id)

            self.assertEqual(decision["action"], "run_tests")
            self.assertEqual(decision["target"], "python3 -m unittest discover -s tests -v")
            self.assertIn("test", decision["reason"])
            self.assertEqual(persisted, decision)

    def test_cli_can_show_subagent_execution_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = str(tmp_path / "miniclaw.db")
            workspace = tmp_path / "workspace"
            (workspace / "tests").mkdir(parents=True)
            (workspace / "tests" / "test_smoke.py").write_text(
                "import unittest\n\n"
                "class SmokeTest(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            self.run_cli(
                "--db",
                db_path,
                "--runtime",
                "subagent",
                "--workspace",
                str(workspace),
                "send",
                "subagent-background: run tests",
            )
            self.run_cli(
                "--db",
                db_path,
                "--runtime",
                "subagent",
                "--workspace",
                str(workspace),
                "run-once",
            )
            listed = self.run_cli("--db", db_path, "background-list")
            task_id = listed.split()[0].removeprefix("#")

            trace = self.run_cli("--db", db_path, "trace-show", task_id)

            self.assertIn("decision: run_tests", trace)
            self.assertIn("target: python3 -m unittest discover -s tests -v", trace)
            self.assertIn("reason: task asks to run tests", trace)
            self.assertIn("observation: Test command output", trace)

    def test_subagent_execution_trace_records_agent_loop_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "miniclaw.db"
            file_tool = RecordingFileTool()
            bash_tool = RecordingBashTool()
            runtime = SubAgentRuntime(file_tool=file_tool, bash_tool=bash_tool)
            app = MiniClawApp.open(db_path, runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: run tests",
            )
            app.orchestrator.run_once()

            task_id = app.background.list()[0]["id"]
            traces = app.store.list_execution_traces(task_id)

            self.assertEqual(
                [trace["event_type"] for trace in traces],
                ["plan", "decision", "tool_call", "observation", "final_result"],
            )
            self.assertIn("run tests", traces[0]["content"])
            self.assertIn("run_tests", traces[1]["content"])
            self.assertIn("python3 -m unittest discover -s tests -v", traces[2]["content"])
            self.assertIn("fake bash output", traces[3]["content"])
            self.assertIn("completed isolated task", traces[4]["content"])

    def test_background_task_completion_becomes_inbound_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db")
            self.assertIsInstance(app.background, BackgroundTaskManager)

            def collect_metrics():
                time.sleep(0.05)
                return "metrics ok"

            task_id = app.background.run(
                group_id="ops",
                command="collect metrics",
                operation=collect_metrics,
            )
            self.assertEqual(app.background.get(task_id)["status"], "running")

            deadline = time.time() + 2
            notifications = []
            while time.time() < deadline:
                notifications = app.background.drain_notifications()
                if notifications:
                    break
                time.sleep(0.01)

            message_ids = app.background.notifications_to_messages(notifications)
            app.orchestrator.run_once()
            outbound = app.store.list_outbound(group_id="ops")

            self.assertEqual(notifications[0]["status"], "completed")
            self.assertEqual(app.background.get(task_id)["result"], "metrics ok")
            self.assertEqual(len(message_ids), 1)
            self.assertIn("Background task", outbound[0]["content"])
            self.assertIn("metrics ok", outbound[0]["content"])

    def test_background_task_state_persists_after_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "miniclaw.db"
            app = MiniClawApp.open(db_path)

            task_id = app.background.run(
                group_id="ops",
                command="collect persisted metrics",
                operation=lambda: "metrics persisted",
            )

            deadline = time.time() + 2
            while time.time() < deadline:
                task = app.background.get(task_id)
                if task["status"] == "completed":
                    break
                time.sleep(0.01)

            reopened = MiniClawApp.open(db_path)
            persisted = reopened.background.get(task_id)

            self.assertEqual(persisted["status"], "completed")
            self.assertEqual(persisted["result"], "metrics persisted")
            self.assertEqual(persisted["command"], "collect persisted metrics")

    def test_cli_can_run_list_and_show_background_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "miniclaw.db")

            started = self.run_cli(
                "--db",
                db_path,
                "background-run",
                "collect metrics",
                "--group",
                "ops",
            )
            task_id = started.strip().split()[-1]

            listed = self.run_cli("--db", db_path, "background-list")
            shown = self.run_cli("--db", db_path, "background-show", task_id)

            self.assertIn("started background task", started)
            self.assertIn(task_id, listed)
            self.assertIn("collect metrics", listed)
            self.assertIn("completed", shown)
            self.assertIn("collect metrics", shown)
            self.assertIn("CLI background task completed: collect metrics", shown)

    def test_cli_can_process_subagent_background_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "miniclaw.db")

            self.run_cli(
                "--db",
                db_path,
                "--runtime",
                "subagent",
                "send",
                "subagent-background: 汇总代码仓库结构",
            )
            processed = self.run_cli("--db", db_path, "--runtime", "subagent", "run-once")
            tasks = self.run_cli("--db", db_path, "background-list")

            self.assertIn("processed message", processed)
            self.assertIn("subagent: 汇总代码仓库结构", tasks)
            self.assertIn("completed", tasks)

    def test_cli_subagent_background_can_observe_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = str(tmp_path / "miniclaw.db")
            workspace = tmp_path / "workspace"
            (workspace / "src").mkdir(parents=True)
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            (workspace / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")

            self.run_cli(
                "--db",
                db_path,
                "--runtime",
                "subagent",
                "--workspace",
                str(workspace),
                "send",
                "subagent-background: inspect workspace",
            )
            self.run_cli("--db", db_path, "--runtime", "subagent", "--workspace", str(workspace), "run-once")
            listed = self.run_cli("--db", db_path, "background-list")
            task_id = listed.split()[0].removeprefix("#")
            shown = self.run_cli("--db", db_path, "background-show", task_id)

            self.assertIn("README.md", shown)
            self.assertIn("src/app.py", shown)


if __name__ == "__main__":
    unittest.main()
