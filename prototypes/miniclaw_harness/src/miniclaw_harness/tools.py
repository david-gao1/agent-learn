from __future__ import annotations

import ast
import contextlib
import io
import shlex
import subprocess
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

    def read_file(self, relative_path: str, max_chars: int = 1200) -> str:
        root = self.workspace.resolve()
        target = (root / relative_path).resolve()
        if target != root and root not in target.parents:
            raise ValueError(f"path escapes workspace: {relative_path}")
        if not target.is_file():
            raise FileNotFoundError(relative_path)
        return target.read_text(encoding="utf-8")[:max_chars]

    def boundary(self) -> dict:
        return {
            "root": "workspace",
            "path_escape": "blocked",
            "hidden_dirs": "ignored",
            "read_limit": "max_chars",
        }


class BashTool:
    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)

    def run(self, command: str, timeout: float = 5, max_output_chars: int = 2000) -> str:
        args = shlex.split(command)
        if not args:
            raise ValueError("empty command")
        if not self._is_allowed(args):
            raise ValueError(f"command is not allowed: {command}")

        completed = subprocess.run(
            args,
            cwd=self.workspace,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = completed.stdout
        if completed.stderr:
            output = f"{output}{completed.stderr}"
        if completed.returncode != 0:
            output = f"exit {completed.returncode}\n{output}"
        boundary = "boundary: shell=False; cwd=workspace; allowlist=matched"
        output = f"{output}{boundary}\n"
        return output[:max_output_chars]

    def _is_allowed(self, args: list[str]) -> bool:
        if args in [["pwd"], ["ls"]]:
            return True
        return len(args) >= 3 and args[:3] == ["python3", "-m", "unittest"]


class CodeTool:
    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)

    def run(self, code: str) -> dict:
        self.validate(code)
        namespace = {
            "len": len,
            "list": list,
            "print": print,
            "sorted": sorted,
            "str": str,
            "list_files": self._list_files,
        }
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exec(code, {"__builtins__": {}}, namespace)
        return {
            "status": "ok",
            "result": namespace.get("result"),
            "stdout": stdout.getvalue(),
            "boundary": self.boundary(),
        }

    def validate(self, code: str) -> None:
        tree = ast.parse(code)
        allowed_nodes = (
            ast.Module,
            ast.Assign,
            ast.Expr,
            ast.Call,
            ast.Name,
            ast.Load,
            ast.Store,
            ast.Constant,
            ast.List,
            ast.Tuple,
            ast.BinOp,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.For,
            ast.Compare,
            ast.Eq,
            ast.NotEq,
            ast.Lt,
            ast.LtE,
            ast.Gt,
            ast.GtE,
        )
        allowed_calls = {"len", "list", "print", "sorted", "str", "list_files"}
        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                raise ValueError(f"code node is not allowed: {type(node).__name__}")
            if isinstance(node, ast.Name) and node.id.startswith("__"):
                raise ValueError("dunder names are not allowed")
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.func.id not in allowed_calls:
                    raise ValueError("function call is not allowed")

    def boundary(self) -> dict:
        return {
            "builtins": "empty",
            "allowed_calls": ["len", "list", "list_files", "print", "sorted", "str"],
            "imports": "blocked",
            "workspace": "read_only_list_files",
        }

    def _list_files(self) -> list[str]:
        return FileTool(self.workspace).list_files(limit=20)
