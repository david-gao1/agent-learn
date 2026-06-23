from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from minimal_harness_agent import HarnessAgent, LocalSkillLoader, TaskStore


def main() -> None:
    state_dir = ROOT / ".demo_state"
    state_dir.mkdir(exist_ok=True)

    agent = HarnessAgent(
        workspace=ROOT,
        skill_loader=LocalSkillLoader(ROOT / "skills"),
        task_store=TaskStore(state_dir / "tasks.json"),
        max_context_messages=4,
    )
    report = agent.run("Analyze this workspace with repo-reading skill")
    print(report)
    print(f"\nTask state: {state_dir / 'tasks.json'}")


if __name__ == "__main__":
    main()
