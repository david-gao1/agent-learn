from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str
    path: Path


class LocalSkillLoader:
    def __init__(self, skills_root: Path):
        self.skills_root = Path(skills_root)

    def list_labels(self) -> list[dict[str, str]]:
        labels: list[dict[str, str]] = []
        if not self.skills_root.exists():
            return labels

        for skill_path in sorted(self.skills_root.iterdir()):
            skill_file = skill_path / "SKILL.md"
            if not skill_file.exists():
                continue
            meta = _read_frontmatter(skill_file.read_text(encoding="utf-8"))
            labels.append(
                {
                    "name": meta.get("name", skill_path.name),
                    "description": meta.get("description", ""),
                }
            )
        return labels

    def load(self, name: str) -> Skill:
        skill_file = self.skills_root / name / "SKILL.md"
        if not skill_file.exists():
            raise FileNotFoundError(f"Skill not found: {name}")

        text = skill_file.read_text(encoding="utf-8")
        meta = _read_frontmatter(text)
        return Skill(
            name=meta.get("name", name),
            description=meta.get("description", ""),
            body=text,
            path=skill_file,
        )


def _read_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}

    end = text.find("\n---", 4)
    if end == -1:
        return {}

    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"')
    return meta
