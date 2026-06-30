import os
import json
import subprocess
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
    CodeTool,
    FileTool,
    FileSystemIPC,
    LocalSkillLoader,
    MiniClawApp,
    ModelBackedRuntime,
    SubAgentRuntime,
)
from minimal_harness_agent import OpenAIResponsesModel  # noqa: E402
from main import build_learning_summary, main as miniclaw_cli  # noqa: E402


class RecordingModel:
    def __init__(self):
        self.calls = []

    def complete(self, instructions: str, prompt: str) -> str:
        self.calls.append({"instructions": instructions, "prompt": prompt})
        return "模型回复：已识别 MiniClaw Harness 任务"


class PlanningModel:
    def __init__(self):
        self.calls = []

    def complete(self, instructions: str, prompt: str) -> str:
        self.calls.append({"instructions": instructions, "prompt": prompt})
        return '{"steps": ["list_files", "read_file", "run_tests", "summarize"]}'


class ChattyPlanningModel:
    def complete(self, instructions: str, prompt: str) -> str:
        return 'Here is the plan:\n{"steps": ["list_files", "run_tests", "summarize"]}\nDone.'


class BrokenPlanningModel:
    def complete(self, instructions: str, prompt: str) -> str:
        return "not json"


class IllegalPlanningModel:
    def complete(self, instructions: str, prompt: str) -> str:
        return '{"steps": ["delete_everything"]}'


class CodeActModel:
    def __init__(self, code: str):
        self.code = code
        self.calls = []

    def complete(self, instructions: str, prompt: str) -> str:
        self.calls.append({"instructions": instructions, "prompt": prompt})
        return self.code


class JsonPlanAdapter:
    def __init__(self, model):
        self.model = model

    def complete(self, instructions: str, prompt: str) -> str:
        text = self.model.complete(instructions, prompt)
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= start:
            text = text[start : end + 1]
        parsed = json.loads(text)
        return json.dumps(parsed)


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


class FlakyBashTool:
    def __init__(self):
        self.commands = []
        self.outputs = ["exit 1\nfailed tests", "ok tests"]

    def run(self, command: str) -> str:
        self.commands.append(command)
        return self.outputs.pop(0)


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

    def test_skill_loader_lists_labels_without_loading_full_skill_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp) / "skills"
            skill_dir = skills_root / "repo-reading"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: repo-reading\n"
                "description: Read a repository systematically\n"
                "---\n\n"
                "# Repo Reading\n\n"
                "Secret deep body: inspect tests before editing.\n",
                encoding="utf-8",
            )
            loader = LocalSkillLoader(skills_root)

            labels = loader.list_labels()
            skill = loader.load("repo-reading")

            self.assertEqual(
                labels,
                [
                    {
                        "name": "repo-reading",
                        "description": "Read a repository systematically",
                    }
                ],
            )
            self.assertNotIn("Secret deep body", str(labels))
            self.assertIn("Secret deep body", skill.body)

    def test_bash_tool_runs_allowlisted_commands_in_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")

            output = BashTool(workspace).run("ls")

            self.assertIn("README.md", output)
            self.assertIn("boundary: shell=False", output)
            self.assertIn("cwd=workspace", output)
            self.assertIn("allowlist=matched", output)

    def test_bash_tool_blocks_unapproved_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()

            with self.assertRaises(ValueError):
                BashTool(workspace).run("rm -rf .")

    def test_code_tool_executes_limited_python_and_blocks_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            tool = CodeTool(workspace)

            result = tool.run(
                "files = list_files()\n"
                "result = len(files)\n"
                "print(result)"
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["result"], 1)
            self.assertEqual(result["stdout"].strip(), "1")
            self.assertEqual(
                result["boundary"],
                {
                    "builtins": "empty",
                    "allowed_calls": ["len", "list", "list_files", "print", "sorted", "str"],
                    "imports": "blocked",
                    "workspace": "read_only_list_files",
                },
            )
            with self.assertRaises(ValueError):
                tool.run("import os\nresult = os.listdir('.')")

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

    def test_store_persists_and_searches_memory_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "miniclaw.db"
            app = MiniClawApp.open(db_path)

            memory_id = app.store.add_memory(
                kind="repo_analysis",
                topic="analyze repo",
                content="Repo analysis summary: files=observed.py; tests=ok",
                source_task_id="task-1",
            )
            reopened = MiniClawApp.open(db_path)
            memories = reopened.store.search_memories("repo", limit=5)

            self.assertEqual(memory_id, 1)
            self.assertEqual(len(memories), 1)
            self.assertEqual(memories[0]["kind"], "repo_analysis")
            self.assertEqual(memories[0]["topic"], "analyze repo")
            self.assertEqual(memories[0]["source_task_id"], "task-1")
            self.assertIn("observed.py", memories[0]["content"])

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

    @unittest.skipUnless(
        os.environ.get("RUN_REAL_MODEL_TESTS") == "1" and os.environ.get("OPENAI_API_KEY"),
        "Set RUN_REAL_MODEL_TESTS=1 and OPENAI_API_KEY to call a real model",
    )
    def test_miniclaw_real_model_planner_smoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "miniclaw.db"
            workspace = Path(tmp) / "workspace"
            (workspace / "tests").mkdir(parents=True)
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            (workspace / "tests" / "test_smoke.py").write_text(
                "import unittest\n\n"
                "class SmokeTest(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            runtime = SubAgentRuntime(
                workspace=workspace,
                planner=JsonPlanAdapter(OpenAIResponsesModel.from_env()),
            )
            app = MiniClawApp.open(db_path, runtime=runtime)

            app.channel.send(
                group_id="real-model",
                user_id="user-1",
                content="subagent-background: analyze repo with model plan",
            )
            app.orchestrator.run_once()

            task_id = app.background.list()[0]["id"]
            state = app.store.get_task_state(task_id)
            traces = app.store.list_execution_traces(task_id)

            self.assertEqual(state["plan_source"], "model")
            self.assertEqual(state["test_status"], "completed")
            self.assertTrue(any(trace["event_type"] == "model_plan" for trace in traces))

    @unittest.skipUnless(
        os.environ.get("RUN_REAL_MODEL_TESTS") == "1" and os.environ.get("OPENAI_API_KEY"),
        "Set RUN_REAL_MODEL_TESTS=1 and OPENAI_API_KEY to call a real model",
    )
    def test_miniclaw_real_model_codeact_smoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "miniclaw.db"
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            runtime = SubAgentRuntime(
                workspace=workspace,
                planner=OpenAIResponsesModel.from_env(),
            )
            app = MiniClawApp.open(db_path, runtime=runtime)

            app.channel.send(
                group_id="real-model",
                user_id="user-1",
                content="subagent-background: codeact count files with model code",
            )
            app.orchestrator.run_once()

            task_id = app.background.list()[0]["id"]
            state = app.store.get_task_state(task_id)
            traces = app.store.list_execution_traces(task_id)

            self.assertEqual(state["kind"], "codeact")
            self.assertEqual(state["status"], "completed")
            self.assertIn(state["code_source"], {"model", "rule_fallback"})
            self.assertTrue(any(trace["event_type"] == "model_code" for trace in traces))

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

    def test_subagent_routes_codeact_task_to_restricted_code_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            runtime = SubAgentRuntime(workspace=workspace)
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db", runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: codeact count files",
            )
            app.orchestrator.run_once()

            task_id = app.background.list()[0]["id"]
            state = app.store.get_task_state(task_id)
            traces = app.store.list_execution_traces(task_id)
            task = app.background.get(task_id)

            self.assertEqual(task["status"], "completed")
            self.assertEqual(runtime.decisions[-1].action, "codeact")
            self.assertEqual(state["kind"], "codeact")
            self.assertEqual(state["status"], "completed")
            self.assertEqual(state["result"], 1)
            self.assertEqual(state["code_safety_status"], "trusted_rule")
            self.assertEqual(state["code_boundary"]["imports"], "blocked")
            self.assertEqual(state["code_boundary"]["builtins"], "empty")
            self.assertIn("codeact", [trace["event_type"] for trace in traces])
            self.assertIn("CodeTool.run", "\n".join(trace["content"] for trace in traces))

    def test_subagent_codeact_can_use_model_generated_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            model = CodeActModel("files = list_files()\nresult = len(files) + 1\nprint(result)")
            runtime = SubAgentRuntime(workspace=workspace, planner=model)
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db", runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: codeact count files with model code",
            )
            app.orchestrator.run_once()

            task_id = app.background.list()[0]["id"]
            state = app.store.get_task_state(task_id)
            traces = app.store.list_execution_traces(task_id)

            self.assertEqual(state["code_source"], "model")
            self.assertEqual(state["code_safety_status"], "accepted")
            self.assertEqual(state["result"], 2)
            self.assertIn("Generate restricted Python", model.calls[0]["instructions"])
            self.assertIn("codeact count files", model.calls[0]["prompt"])
            self.assertIn("model_code", [trace["event_type"] for trace in traces])

    def test_subagent_codeact_falls_back_when_model_code_is_unsafe(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            model = CodeActModel("import os\nresult = os.listdir('.')")
            runtime = SubAgentRuntime(workspace=workspace, planner=model)
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db", runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: codeact count files with unsafe model code",
            )
            app.orchestrator.run_once()

            task_id = app.background.list()[0]["id"]
            state = app.store.get_task_state(task_id)
            traces = app.store.list_execution_traces(task_id)

            self.assertEqual(state["code_source"], "rule_fallback")
            self.assertEqual(state["code_safety_status"], "rejected_fallback")
            self.assertEqual(state["result"], 1)
            self.assertIn("code_error", state)
            self.assertIn("code_error", [trace["event_type"] for trace in traces])
            self.assertIn("model_code", [trace["event_type"] for trace in traces])

    def test_subagent_run_tests_can_pause_for_human_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "miniclaw.db"
            bash_tool = RecordingBashTool()
            runtime = SubAgentRuntime(file_tool=RecordingFileTool(), bash_tool=bash_tool)
            app = MiniClawApp.open(db_path, runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: run tests requires approval",
            )
            app.orchestrator.run_once()

            task_id = app.background.list()[0]["id"]
            task = app.background.get(task_id)
            state = app.store.get_task_state(task_id)
            approval = app.store.get_approval(task_id)
            traces = app.store.list_execution_traces(task_id)

            self.assertEqual(task["status"], "waiting_approval")
            self.assertEqual(bash_tool.commands, [])
            self.assertEqual(state["status"], "waiting_approval")
            self.assertEqual(state["approval_status"], "pending")
            self.assertEqual(approval["status"], "pending")
            self.assertIn("run tests requires approval", approval["reason"])
            self.assertIn("approval_request", [trace["event_type"] for trace in traces])

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
            observations = self.run_cli(
                "--db",
                db_path,
                "trace-show",
                task_id,
                "--event",
                "observation",
            )

            self.assertIn("decision: run_tests", trace)
            self.assertIn("target: python3 -m unittest discover -s tests -v", trace)
            self.assertIn("reason: task asks to run tests", trace)
            self.assertIn("observation: Test command output", trace)
            self.assertIn("observation: Test command output", observations)
            self.assertNotIn("decision: run_tests", observations)
            self.assertNotIn("tool_call:", observations)

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

    def test_subagent_repo_analysis_runs_multiple_tool_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "miniclaw.db"
            file_tool = RecordingFileTool()
            bash_tool = RecordingBashTool()
            runtime = SubAgentRuntime(file_tool=file_tool, bash_tool=bash_tool)
            app = MiniClawApp.open(db_path, runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: analyze repo",
            )
            app.orchestrator.run_once()

            task_id = app.background.list()[0]["id"]
            traces = app.store.list_execution_traces(task_id)
            state = app.store.get_task_state(task_id)
            summary_report = build_learning_summary(app, task_id)
            events = [trace["event_type"] for trace in traces]
            final_result = traces[-1]["content"]

            self.assertEqual(file_tool.calls, 1)
            self.assertEqual(file_tool.reads, [("observed.py", 400)])
            self.assertEqual(bash_tool.commands, ["python3 -m unittest discover -s tests -v"])
            self.assertEqual(
                events,
                [
                    "plan",
                    "decision",
                    "tool_call",
                    "observation",
                    "tool_call",
                    "observation",
                    "tool_call",
                    "observation",
                    "final_result",
                ],
            )
            self.assertIn("FileTool.list_files", traces[2]["content"])
            self.assertIn("observed.py", traces[3]["content"])
            self.assertIn("FileTool.read_file", traces[4]["content"])
            self.assertIn("fake observed content", traces[5]["content"])
            self.assertIn("BashTool.run", traces[6]["content"])
            self.assertIn("fake bash output", traces[7]["content"])
            self.assertIn("Repo analysis summary", final_result)
            self.assertEqual(
                state["tools_used"],
                ["FileTool.list_files", "FileTool.read_file", "BashTool.run"],
            )
            self.assertIn("- mechanism: Repository Analysis Agent Loop", summary_report)
            self.assertIn("- action_boundary: FileTool/BashTool", summary_report)
            self.assertIn(
                "- state_evidence: tools_used=FileTool.list_files, FileTool.read_file, BashTool.run",
                summary_report,
            )
            self.assertIn("- loop_evidence: plan -> tool_call -> observation -> final_result", summary_report)

    def test_subagent_repo_analysis_writes_and_recalls_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "miniclaw.db"
            file_tool = RecordingFileTool()
            bash_tool = RecordingBashTool()
            runtime = SubAgentRuntime(file_tool=file_tool, bash_tool=bash_tool)
            app = MiniClawApp.open(db_path, runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: analyze repo",
            )
            app.orchestrator.run_once()
            first_task_id = app.background.list()[0]["id"]
            first_memories = app.store.search_memories("repo", limit=5)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: analyze repo again",
            )
            app.orchestrator.run_once()
            second_task_id = app.background.list()[1]["id"]
            second_state = app.store.get_task_state(second_task_id)
            second_traces = app.store.list_execution_traces(second_task_id)

            self.assertEqual(first_memories[0]["source_task_id"], first_task_id)
            self.assertIn("Repo analysis summary", first_memories[0]["content"])
            self.assertIn("memory_recall", [trace["event_type"] for trace in second_traces])
            self.assertEqual(second_state["memory_count"], 1)
            self.assertIn(first_task_id, second_state["memory_summary"])

    def test_subagent_repo_analysis_can_use_model_planner(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "miniclaw.db"
            planner = PlanningModel()
            file_tool = RecordingFileTool()
            bash_tool = RecordingBashTool()
            runtime = SubAgentRuntime(
                file_tool=file_tool,
                bash_tool=bash_tool,
                planner=planner,
            )
            app = MiniClawApp.open(db_path, runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: analyze repo with model plan",
            )
            app.orchestrator.run_once()

            task_id = app.background.list()[0]["id"]
            traces = app.store.list_execution_traces(task_id)
            state = app.store.get_task_state(task_id)

            self.assertEqual(file_tool.calls, 1)
            self.assertEqual(file_tool.reads, [("observed.py", 400)])
            self.assertEqual(bash_tool.commands, ["python3 -m unittest discover -s tests -v"])
            self.assertIn("analyze repo with model plan", planner.calls[0]["prompt"])
            self.assertIn("return JSON", planner.calls[0]["instructions"])
            self.assertEqual(state["plan_source"], "model")
            self.assertIn("model_plan", [trace["event_type"] for trace in traces])
            self.assertIn("list_files -> read_file -> run_tests -> summarize", "\n".join(trace["content"] for trace in traces))

    def test_subagent_repo_analysis_loads_matching_skill_progressively(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            skills_root = tmp_path / "skills"
            skill_dir = skills_root / "repo-reading"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: repo-reading\n"
                "description: Use for repository analysis tasks\n"
                "---\n\n"
                "# Repo Reading Skill\n\n"
                "Read README, tests, and entrypoints before summarizing.\n",
                encoding="utf-8",
            )
            file_tool = RecordingFileTool()
            bash_tool = RecordingBashTool()
            runtime = SubAgentRuntime(
                file_tool=file_tool,
                bash_tool=bash_tool,
                skill_loader=LocalSkillLoader(skills_root),
            )
            app = MiniClawApp.open(tmp_path / "miniclaw.db", runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: analyze repo with repo-reading skill",
            )
            app.orchestrator.run_once()

            task_id = app.background.list()[0]["id"]
            state = app.store.get_task_state(task_id)
            traces = app.store.list_execution_traces(task_id)

            self.assertEqual(state["skill"], "repo-reading")
            self.assertIn("Read README, tests, and entrypoints", state["skill_summary"])
            self.assertIn("skill_load", [trace["event_type"] for trace in traces])
            self.assertIn("repo-reading", "\n".join(trace["content"] for trace in traces))

    def test_subagent_model_planner_extracts_json_from_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = SubAgentRuntime(
                file_tool=RecordingFileTool(),
                bash_tool=RecordingBashTool(),
                planner=ChattyPlanningModel(),
            )
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db", runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: analyze repo with chatty model plan",
            )
            app.orchestrator.run_once()

            task_id = app.background.list()[0]["id"]
            state = app.store.get_task_state(task_id)
            traces = app.store.list_execution_traces(task_id)

            self.assertEqual(state["plan_source"], "model")
            self.assertIn("list_files -> run_tests -> summarize", "\n".join(trace["content"] for trace in traces))

    def test_subagent_model_planner_falls_back_on_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_tool = RecordingFileTool()
            bash_tool = RecordingBashTool()
            runtime = SubAgentRuntime(
                file_tool=file_tool,
                bash_tool=bash_tool,
                planner=BrokenPlanningModel(),
            )
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db", runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: analyze repo with broken model plan",
            )
            app.orchestrator.run_once()

            task_id = app.background.list()[0]["id"]
            state = app.store.get_task_state(task_id)
            traces = app.store.list_execution_traces(task_id)

            self.assertEqual(file_tool.calls, 1)
            self.assertEqual(file_tool.reads, [("observed.py", 400)])
            self.assertEqual(bash_tool.commands, ["python3 -m unittest discover -s tests -v"])
            self.assertEqual(state["plan_source"], "rule_fallback")
            self.assertIn("planner_error", state)
            self.assertEqual(state["test_status"], "completed")
            self.assertIn("planner_error", [trace["event_type"] for trace in traces])
            self.assertIn("fallback: list_files -> read_file -> run_tests -> summarize", "\n".join(trace["content"] for trace in traces))

    def test_subagent_model_planner_falls_back_on_invalid_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_tool = RecordingFileTool()
            bash_tool = RecordingBashTool()
            runtime = SubAgentRuntime(
                file_tool=file_tool,
                bash_tool=bash_tool,
                planner=IllegalPlanningModel(),
            )
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db", runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: analyze repo with illegal model plan",
            )
            app.orchestrator.run_once()

            task_id = app.background.list()[0]["id"]
            state = app.store.get_task_state(task_id)
            traces = app.store.list_execution_traces(task_id)

            self.assertEqual(file_tool.calls, 1)
            self.assertEqual(file_tool.reads, [("observed.py", 400)])
            self.assertEqual(bash_tool.commands, ["python3 -m unittest discover -s tests -v"])
            self.assertEqual(state["plan_source"], "rule_fallback")
            self.assertIn("no allowed steps", state["planner_error"])
            self.assertEqual(state["test_status"], "completed")
            self.assertIn("planner_error", [trace["event_type"] for trace in traces])
            self.assertIn("fallback: list_files -> read_file -> run_tests -> summarize", "\n".join(trace["content"] for trace in traces))

    def test_repo_analysis_persists_structured_task_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "miniclaw.db"
            file_tool = RecordingFileTool()
            bash_tool = RecordingBashTool()
            runtime = SubAgentRuntime(file_tool=file_tool, bash_tool=bash_tool)
            app = MiniClawApp.open(db_path, runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: analyze repo",
            )
            app.orchestrator.run_once()

            task_id = app.background.list()[0]["id"]
            state = app.store.get_task_state(task_id)
            traces = app.store.list_execution_traces(task_id)
            observation_times = [
                trace["created_at"]
                for trace in traces
                if trace["event_type"] == "observation"
            ]
            reopened = MiniClawApp.open(db_path)
            persisted = reopened.store.get_task_state(task_id)

            self.assertEqual(state["files"], ["observed.py"])
            self.assertEqual(state["preview_file"], "observed.py")
            self.assertEqual(state["preview"], "fake observed content")
            self.assertEqual(state["test_status"], "completed")
            self.assertIn("fake bash output", state["test_output"])
            self.assertIn("Repo analysis summary", state["summary"])
            self.assertEqual(state["last_observation_at"], observation_times[-1])
            self.assertEqual(persisted, state)

    def test_repo_analysis_reuses_existing_state_and_skips_completed_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "miniclaw.db"
            file_tool = RecordingFileTool()
            bash_tool = RecordingBashTool()
            runtime = SubAgentRuntime(file_tool=file_tool, bash_tool=bash_tool)
            app = MiniClawApp.open(db_path, runtime=runtime)

            task_id = app.background.run(
                group_id="learning",
                command="subagent: analyze repo",
                operation=lambda active_task_id: runtime._background_result(
                    active_task_id,
                    "analyze repo",
                    runtime._decide_tool("analyze repo"),
                ),
                start=False,
                pass_task_id=True,
            )
            app.store.set_task_state(
                task_id,
                {
                    "kind": "repo_analysis",
                    "files": ["cached.py"],
                    "preview_file": "cached.py",
                    "preview": "cached preview",
                },
            )

            app.background.start(
                task_id,
                lambda active_task_id: runtime._background_result(
                    active_task_id,
                    "analyze repo",
                    runtime._decide_tool("analyze repo"),
                ),
                pass_task_id=True,
            )
            deadline = time.time() + 2
            while time.time() < deadline:
                if app.background.get(task_id)["status"] != "running":
                    break
                time.sleep(0.01)

            state = app.store.get_task_state(task_id)
            traces = app.store.list_execution_traces(task_id)

            self.assertEqual(file_tool.calls, 0)
            self.assertEqual(file_tool.reads, [])
            self.assertEqual(bash_tool.commands, ["python3 -m unittest discover -s tests -v"])
            self.assertEqual(state["files"], ["cached.py"])
            self.assertEqual(state["preview"], "cached preview")
            self.assertEqual(state["test_status"], "completed")
            self.assertIn("fake bash output", state["test_output"])
            self.assertIn("Reused task state", traces[0]["content"])
            self.assertIn("BashTool.run", traces[-2]["content"])

    def test_cli_can_show_structured_task_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = str(tmp_path / "miniclaw.db")
            workspace = tmp_path / "workspace"
            (workspace / "tests").mkdir(parents=True)
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
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
                "subagent-background: analyze repo",
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

            state = self.run_cli("--db", db_path, "state-show", task_id)

            self.assertIn("kind: repo_analysis", state)
            self.assertIn("files: README.md, tests/test_smoke.py", state)
            self.assertIn("preview_file: README.md", state)
            self.assertIn("test_status: completed", state)
            self.assertIn("summary: Repo analysis summary", state)

    def test_cli_can_load_skills_for_subagent_repo_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = str(tmp_path / "miniclaw.db")
            workspace = tmp_path / "workspace"
            skills_root = tmp_path / "skills"
            skill_dir = skills_root / "repo-reading"
            (workspace / "tests").mkdir(parents=True)
            skill_dir.mkdir(parents=True)
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            (workspace / "tests" / "test_smoke.py").write_text(
                "import unittest\n\n"
                "class SmokeTest(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: repo-reading\n"
                "description: Use for repository analysis tasks\n"
                "---\n\n"
                "# Repo Reading Skill\n\n"
                "Read README before summarizing.\n",
                encoding="utf-8",
            )

            self.run_cli(
                "--db",
                db_path,
                "--runtime",
                "subagent",
                "--workspace",
                str(workspace),
                "--skills-root",
                str(skills_root),
                "send",
                "subagent-background: analyze repo with repo-reading skill",
            )
            self.run_cli(
                "--db",
                db_path,
                "--runtime",
                "subagent",
                "--workspace",
                str(workspace),
                "--skills-root",
                str(skills_root),
                "run-once",
            )
            listed = self.run_cli("--db", db_path, "background-list")
            task_id = listed.split()[0].removeprefix("#")

            state = self.run_cli("--db", db_path, "state-show", task_id)

            self.assertIn("skill: repo-reading", state)
            self.assertIn("skill_summary:", state)

    def test_cli_can_list_persisted_memories(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = str(tmp_path / "miniclaw.db")
            workspace = tmp_path / "workspace"
            (workspace / "tests").mkdir(parents=True)
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
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
                "subagent-background: analyze repo",
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

            output = self.run_cli("--db", db_path, "memory-list", "repo")

            self.assertIn("repo_analysis", output)
            self.assertIn("Repo analysis summary", output)
            self.assertIn("state: status=completed", output)
            self.assertIn("test_status=completed", output)
            self.assertIn("tools_used=FileTool.list_files, FileTool.read_file, BashTool.run", output)

    def test_cli_can_run_codeact_subagent_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = str(tmp_path / "miniclaw.db")
            workspace = tmp_path / "workspace"
            workspace.mkdir()
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")

            self.run_cli(
                "--db",
                db_path,
                "--runtime",
                "subagent",
                "--workspace",
                str(workspace),
                "send",
                "subagent-background: codeact count files",
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

            state = self.run_cli("--db", db_path, "state-show", task_id)
            trace = self.run_cli("--db", db_path, "trace-show", task_id)

            self.assertIn("kind: codeact", state)
            self.assertIn("result: 1", state)
            self.assertIn("codeact: CodeTool.run", trace)
            self.assertIn("observation: CodeAct output", trace)

    def test_cli_can_export_task_report_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = str(tmp_path / "miniclaw.db")
            workspace = tmp_path / "workspace"
            workspace.mkdir()
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")

            self.run_cli(
                "--db",
                db_path,
                "--runtime",
                "subagent",
                "--workspace",
                str(workspace),
                "send",
                "subagent-background: codeact count files",
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

            report = self.run_cli("--db", db_path, "task-report", task_id)
            summary = self.run_cli("--db", db_path, "task-report", task_id, "--summary")

            self.assertIn(f"# MiniClaw Task Report: {task_id}", report)
            self.assertIn("## Task", report)
            self.assertIn("subagent: codeact count files", report)
            self.assertIn("## Tool Decision", report)
            self.assertIn("action: codeact", report)
            self.assertIn("## Trace", report)
            self.assertIn("- codeact: CodeTool.run", report)
            self.assertIn("## State", report)
            self.assertIn("- kind: codeact", report)
            self.assertIn("- result: 1", report)
            self.assertIn("## State Field Notes", report)
            self.assertIn(
                "- code_safety_status: records whether CodeAct code was trusted rule code, accepted model code, or rejected model code fallback.",
                report,
            )
            self.assertIn(f"# MiniClaw Learning Summary: {task_id}", summary)
            self.assertIn("- mechanism: CodeAct", summary)
            self.assertIn("- action_boundary: CodeTool.run", summary)
            self.assertIn("- state_evidence: code_safety_status=trusted_rule", summary)
            self.assertNotIn("## Trace", summary)
            self.assertNotIn("## State", summary)

    def test_cli_learn_check_runs_short_learning_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = str(tmp_path / "miniclaw.db")
            workspace = tmp_path / "workspace"
            (workspace / "tests").mkdir(parents=True)
            (workspace / "README.md").write_text("# Demo\n", encoding="utf-8")
            (workspace / "tests" / "test_smoke.py").write_text(
                "import unittest\n\n"
                "class SmokeTest(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            output = self.run_cli("--db", db_path, "--workspace", str(workspace), "learn-check")

            self.assertIn("PASS loop: plan -> tool_call -> observation -> final_result", output)
            self.assertIn("PASS codeact: code_safety_status=trusted_rule", output)
            self.assertIn("PASS code-boundary: imports=blocked; builtins=empty", output)
            self.assertIn("PASS memory: repo_analysis memory stored", output)
            self.assertIn("PASS compact: compact_summary stored", output)
            self.assertIn("PASS boundary: shell=False; cwd=workspace; allowlist=matched", output)
            self.assertIn("PASS approval: next_step=approve-task", output)
            self.assertIn("PASS summary: MiniClaw Learning Summary", output)

    def test_cli_can_approve_waiting_test_task_and_resume_execution(self):
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
                "subagent-background: run tests requires approval",
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
            summary = self.run_cli("--db", db_path, "task-report", task_id, "--summary")

            self.assertIn(f"next_step=approve-task {task_id}", listed)
            self.assertIn("- mechanism: Human Approval", summary)
            self.assertIn("- state_evidence: approval_status=pending", summary)
            self.assertIn(f"- next_step: approve-task {task_id}", summary)

            approval = self.run_cli(
                "--db",
                db_path,
                "--runtime",
                "subagent",
                "--workspace",
                str(workspace),
                "approve-task",
                task_id,
            )
            task = self.run_cli("--db", db_path, "background-show", task_id)
            trace = self.run_cli("--db", db_path, "trace-show", task_id)

            self.assertIn(f"approved background task {task_id}", approval)
            self.assertIn("status=completed", task)
            self.assertIn("approval: approved", trace)
            self.assertIn("observation: Test command output", trace)

    def test_cli_can_resume_repo_analysis_from_task_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = tmp_path / "miniclaw.db"
            workspace = tmp_path / "workspace"
            (workspace / "tests").mkdir(parents=True)
            (workspace / "cached.py").write_text("print('cached')\n", encoding="utf-8")
            (workspace / "tests" / "test_smoke.py").write_text(
                "import unittest\n\n"
                "class SmokeTest(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            app = MiniClawApp.open(db_path)
            task_id = "resume01"
            app.store.add_background_task(
                task_id=task_id,
                group_id="learning",
                command="subagent: analyze repo",
                status="paused",
            )
            app.store.set_task_state(
                task_id,
                {
                    "kind": "repo_analysis",
                    "files": ["cached.py"],
                    "preview_file": "cached.py",
                    "preview": "print('cached')",
                },
            )

            resumed = self.run_cli(
                "--db",
                str(db_path),
                "--runtime",
                "subagent",
                "--workspace",
                str(workspace),
                "resume-task",
                task_id,
            )
            trace = self.run_cli("--db", str(db_path), "trace-show", task_id)
            state = self.run_cli("--db", str(db_path), "state-show", task_id)

            self.assertIn("resumed background task resume01", resumed)
            self.assertIn("Reused task state", trace)
            self.assertIn("tool_call: BashTool.run", trace)
            self.assertIn("test_status: completed", state)
            self.assertIn("summary: Repo analysis summary", state)

    def test_repo_analysis_marks_failed_tests_as_blocked_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "miniclaw.db"
            file_tool = RecordingFileTool()
            bash_tool = FlakyBashTool()
            runtime = SubAgentRuntime(file_tool=file_tool, bash_tool=bash_tool)
            app = MiniClawApp.open(db_path, runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: analyze repo",
            )
            app.orchestrator.run_once()

            task_id = app.background.list()[0]["id"]
            state = app.store.get_task_state(task_id)
            task = app.background.get(task_id)
            listed = self.run_cli("--db", str(db_path), "background-list")
            summary = build_learning_summary(app, task_id)

            self.assertEqual(task["status"], "error")
            self.assertEqual(state["status"], "blocked")
            self.assertEqual(state["test_status"], "failed")
            self.assertEqual(state["files"], ["observed.py"])
            self.assertEqual(state["preview"], "fake observed content")
            self.assertIn("failed tests", state["blocked_reason"])
            self.assertIn(f"next_step=resume-task {task_id}", listed)
            self.assertIn("- state_evidence: test_status=failed", summary)
            self.assertIn(f"- next_step: resume-task {task_id}", summary)

    def test_repo_analysis_can_resume_after_blocked_test_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "miniclaw.db"
            file_tool = RecordingFileTool()
            bash_tool = FlakyBashTool()
            runtime = SubAgentRuntime(file_tool=file_tool, bash_tool=bash_tool)
            app = MiniClawApp.open(db_path, runtime=runtime)

            app.channel.send(
                group_id="learning",
                user_id="user-1",
                content="subagent-background: analyze repo",
            )
            app.orchestrator.run_once()
            task_id = app.background.list()[0]["id"]

            runtime.resume_background_task(task_id, "analyze repo")
            deadline = time.time() + 2
            while time.time() < deadline:
                if app.background.get(task_id)["status"] != "running":
                    break
                time.sleep(0.01)

            state = app.store.get_task_state(task_id)
            task = app.background.get(task_id)

            self.assertEqual(file_tool.calls, 1)
            self.assertEqual(file_tool.reads, [("observed.py", 400)])
            self.assertEqual(bash_tool.commands, ["python3 -m unittest discover -s tests -v"] * 2)
            self.assertEqual(task["status"], "completed")
            self.assertEqual(state["status"], "completed")
            self.assertEqual(state["test_status"], "completed")
            self.assertNotIn("blocked_reason", state)
            self.assertIn("ok tests", state["test_output"])

    def test_compact_task_trace_summarizes_old_events_into_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db")
            task_id = "compact1"
            app.store.add_background_task(
                task_id=task_id,
                group_id="learning",
                command="subagent: analyze repo",
                status="completed",
                result="done",
            )
            app.store.set_task_state(
                task_id,
                {
                    "kind": "repo_analysis",
                    "files": ["README.md", "tests/test_smoke.py"],
                    "preview_file": "README.md",
                    "status": "completed",
                    "test_status": "completed",
                    "summary": "Repo analysis summary",
                },
            )
            for index in range(8):
                app.store.add_execution_trace(task_id, "observation", f"event {index}")

            app.store.compact_task_trace(task_id, keep_recent=3)

            state = app.store.get_task_state(task_id)
            traces = app.store.list_execution_traces(task_id)

            self.assertIn("compact_summary", state)
            self.assertIn("files=README.md, tests/test_smoke.py", state["compact_summary"])
            self.assertIn("test_status=completed", state["compact_summary"])
            self.assertIn("compacted 8 events", traces[0]["content"])
            self.assertEqual([trace["content"] for trace in traces[1:]], ["event 5", "event 6", "event 7"])

    def test_cli_can_compact_task_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "miniclaw.db"
            app = MiniClawApp.open(db_path)
            task_id = "compact2"
            app.store.add_background_task(
                task_id=task_id,
                group_id="learning",
                command="subagent: analyze repo",
                status="completed",
                result="done",
            )
            app.store.set_task_state(task_id, {"kind": "repo_analysis", "test_status": "completed"})
            for index in range(6):
                app.store.add_execution_trace(task_id, "observation", f"event {index}")

            output = self.run_cli("--db", str(db_path), "compact-task", task_id, "--keep-recent", "2")
            trace = self.run_cli("--db", str(db_path), "trace-show", task_id)
            state = self.run_cli("--db", str(db_path), "state-show", task_id)

            self.assertIn("compacted task compact2", output)
            self.assertIn("compact: compacted 6 events", trace)
            self.assertIn("observation: event 4", trace)
            self.assertIn("observation: event 5", trace)
            self.assertNotIn("observation: event 0", trace)
            self.assertIn("compact_summary:", state)

    def test_trace_auto_compacts_when_threshold_is_exceeded(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db")
            task_id = "auto1"
            app.store.add_background_task(
                task_id=task_id,
                group_id="learning",
                command="subagent: analyze repo",
                status="completed",
                result="done",
            )
            app.store.set_task_state(
                task_id,
                {
                    "kind": "repo_analysis",
                    "files": ["README.md"],
                    "status": "completed",
                    "test_status": "completed",
                },
            )

            for index in range(7):
                app.store.add_execution_trace(
                    task_id,
                    "observation",
                    f"event {index}",
                    compact_threshold=6,
                    keep_recent=2,
                )

            state = app.store.get_task_state(task_id)
            traces = app.store.list_execution_traces(task_id)

            self.assertIn("compact_summary", state)
            self.assertIn("events=7", state["compact_summary"])
            self.assertEqual([trace["event_type"] for trace in traces], ["compact", "observation", "observation"])
            self.assertEqual([trace["content"] for trace in traces[1:]], ["event 5", "event 6"])

    def test_trace_auto_compact_waits_until_task_state_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = MiniClawApp.open(Path(tmp) / "miniclaw.db")
            task_id = "auto2"
            app.store.add_background_task(
                task_id=task_id,
                group_id="learning",
                command="subagent: analyze repo",
                status="running",
            )

            for index in range(7):
                app.store.add_execution_trace(
                    task_id,
                    "observation",
                    f"event {index}",
                    compact_threshold=6,
                    keep_recent=2,
                )

            traces = app.store.list_execution_traces(task_id)

            self.assertEqual(len(traces), 7)
            self.assertEqual(traces[0]["content"], "event 0")

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

    def test_walkthrough_script_exports_learning_evidence(self):
        repo_root = PROJECT_ROOT.parents[1]
        script = repo_root / "scripts" / "run_miniclaw_walkthrough.sh"

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "walkthrough-output"

            result = subprocess.run(
                ["bash", str(script), "--output", str(output_dir)],
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            expected_files = [
                "普通消息.txt",
                "仓库分析-trace.txt",
                "仓库分析-state.txt",
                "memory.txt",
                "codeact-trace.txt",
                "codeact-state.txt",
                "approval-trace.txt",
                "compact-trace.txt",
                "task-report.md",
                "summary.md",
            ]
            for name in expected_files:
                self.assertTrue((output_dir / name).exists(), name)

            summary = (output_dir / "summary.md").read_text(encoding="utf-8")
            repo_trace = (output_dir / "仓库分析-trace.txt").read_text(encoding="utf-8")
            code_state = (output_dir / "codeact-state.txt").read_text(encoding="utf-8")
            approval_trace = (output_dir / "approval-trace.txt").read_text(encoding="utf-8")
            report = (output_dir / "task-report.md").read_text(encoding="utf-8")

            self.assertIn("MiniClaw Walkthrough Evidence", summary)
            self.assertIn("Repo analysis task", summary)
            self.assertIn("CodeAct task", summary)
            self.assertIn("Approval task", summary)
            self.assertIn("tool_call: FileTool.list_files", repo_trace)
            self.assertIn("skill_load: repo-reading", repo_trace)
            self.assertIn("kind: codeact", code_state)
            self.assertIn("approval: approved", approval_trace)
            self.assertIn("# MiniClaw Task Report", report)

    def test_verify_offline_script_runs_all_local_checks(self):
        repo_root = PROJECT_ROOT.parents[1]
        script = repo_root / "scripts" / "verify_offline.sh"

        env = os.environ.copy()
        env["MINICLAW_VERIFY_NESTED"] = "1"

        result = subprocess.run(
            ["bash", str(script)],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        combined = result.stdout + result.stderr
        self.assertIn("MiniClaw tests", combined)
        self.assertIn("minimal harness tests", combined)
        self.assertIn("walkthrough evidence", combined)
        self.assertIn("whitespace check", combined)
        self.assertIn("Offline verification complete", combined)

    def test_verify_real_model_script_requires_openai_api_key(self):
        repo_root = PROJECT_ROOT.parents[1]
        script = repo_root / "scripts" / "verify_real_model.sh"
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        env.pop("RUN_REAL_MODEL_TESTS", None)

        result = subprocess.run(
            ["bash", str(script)],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("OPENAI_API_KEY is required", result.stderr + result.stdout)

    def test_check_external_readiness_reports_local_status(self):
        repo_root = PROJECT_ROOT.parents[1]
        script = repo_root / "scripts" / "check_external_readiness.sh"
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        env.pop("RUN_REAL_MODEL_TESTS", None)

        result = subprocess.run(
            ["bash", str(script)],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        output = result.stdout + result.stderr
        self.assertIn("External Readiness", output)
        self.assertIn("branch:", output)
        self.assertIn("remote:", output)
        self.assertIn("ahead_of_origin:", output)
        self.assertIn("openai_api_key: missing", output)
        self.assertIn("offline_verifier:", output)
        self.assertIn("credential_helper:", output)
        self.assertIn("credential_helper_available:", output)
        self.assertIn("ssh_github_auth:", output)
        self.assertIn("Fix git credential helper or switch to SSH before pushing.", output)
        self.assertIn("Authorize an SSH key with GitHub if using SSH remote.", output)

    def test_makefile_exposes_common_learning_commands(self):
        repo_root = PROJECT_ROOT.parents[1]
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)

        help_result = subprocess.run(
            ["make", "help"],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        readiness_result = subprocess.run(
            ["make", "readiness"],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(help_result.returncode, 0, help_result.stderr + help_result.stdout)
        self.assertEqual(
            readiness_result.returncode,
            0,
            readiness_result.stderr + readiness_result.stdout,
        )
        self.assertIn("verify", help_result.stdout)
        self.assertIn("walkthrough", help_result.stdout)
        self.assertIn("readiness", help_result.stdout)
        self.assertIn("real-model", help_result.stdout)
        self.assertIn("External Readiness", readiness_result.stdout)


if __name__ == "__main__":
    unittest.main()
