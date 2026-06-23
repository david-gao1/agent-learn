import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from minimal_harness_agent import (  # noqa: E402
    HarnessAgent,
    LocalSkillLoader,
    TaskStore,
    compact_messages,
    read_file,
    run_bash,
)


class MinimalHarnessAgentTest(unittest.TestCase):
    def test_skill_loader_reads_labels_before_full_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            skill_dir = tmp_path / "skills" / "repo-reading"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: repo-reading\n"
                "description: Read a small repository and summarize structure.\n"
                "---\n\n"
                "# Repo Reading\n\n"
                "Use `rg --files` first, then inspect entrypoints.\n",
                encoding="utf-8",
            )

            loader = LocalSkillLoader(tmp_path / "skills")

            self.assertEqual(
                loader.list_labels(),
                [
                    {
                        "name": "repo-reading",
                        "description": "Read a small repository and summarize structure.",
                    }
                ],
            )
            full_skill = loader.load("repo-reading")
            self.assertIn("Use `rg --files` first", full_skill.body)

    def test_compact_messages_preserves_recent_context_and_summary(self):
        messages = [
            "User asked for a Harness Agent plan.",
            "Agent inspected the PDF chapter structure.",
            "Agent created OpenSpec documents.",
            "Agent implemented a minimal prototype.",
        ]

        compacted = compact_messages(messages, keep_last=2)

        self.assertEqual(
            compacted,
            [
                "Summary of earlier context: User asked for a Harness Agent plan. Agent inspected the PDF chapter structure.",
                "Agent created OpenSpec documents.",
                "Agent implemented a minimal prototype.",
            ],
        )

    def test_task_store_persists_task_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            store = TaskStore(tmp_path / "tasks.json")

            task_id = store.add("Read chapter 6 and summarize Agent Loop")
            store.update(task_id, "done")

            reloaded = TaskStore(tmp_path / "tasks.json")
            self.assertEqual(
                reloaded.list(),
                [
                    {
                        "id": task_id,
                        "title": "Read chapter 6 and summarize Agent Loop",
                        "status": "done",
                    }
                ],
            )

    def test_tools_read_files_and_block_dangerous_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target = tmp_path / "note.md"
            target.write_text(
                "Harness = model plus operating system around it.\n",
                encoding="utf-8",
            )

            self.assertEqual(
                read_file(target),
                "Harness = model plus operating system around it.\n",
            )
            self.assertIn("Dangerous command blocked", run_bash("rm -rf /", cwd=tmp_path))
            self.assertEqual(run_bash("printf harness", cwd=tmp_path), "harness")

    def test_agent_loop_executes_multistep_plan_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            skill_root = tmp_path / "skills"
            skill_root.mkdir()
            (skill_root / "repo-reading").mkdir()
            (skill_root / "repo-reading" / "SKILL.md").write_text(
                "---\n"
                "name: repo-reading\n"
                "description: Read repository files and produce a short analysis.\n"
                "---\n\n"
                "# Repo Reading\n",
                encoding="utf-8",
            )
            (tmp_path / "sample.py").write_text("print('hello harness')\n", encoding="utf-8")

            agent = HarnessAgent(
                workspace=tmp_path,
                skill_loader=LocalSkillLoader(skill_root),
                task_store=TaskStore(tmp_path / "tasks.json"),
                max_context_messages=3,
            )

            report = agent.run("Analyze this workspace with repo-reading skill")

            self.assertIn("Loaded skill: repo-reading", report)
            self.assertIn("Workspace files:", report)
            self.assertIn("sample.py", report)
            self.assertIn("Task status: done", report)
            self.assertIn("Context messages:", report)
            persisted = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted[0]["status"], "done")


if __name__ == "__main__":
    unittest.main()
