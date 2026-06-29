from __future__ import annotations

from pathlib import Path


class FileTool:
    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)

    def list_files(self, limit: int = 20) -> list[str]:
        root = self.workspace.resolve()
        ignored_dirs = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", "node_modules"}
        files: list[str] = []
        for path in sorted(root.rglob("*")):
            if len(files) >= limit:
                break
            relative_parts = path.relative_to(root).parts
            if any(part in ignored_dirs or part.startswith(".") for part in relative_parts):
                continue
            if path.is_file():
                files.append(path.relative_to(root).as_posix())
        return files
