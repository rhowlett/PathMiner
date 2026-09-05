#!/usr/bin/env python3
"""Shared helpers for PathMiner AI session launch automation."""

from __future__ import annotations

import csv
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


MODEL_IDS = {
    "Haiku-4.5": "claude-haiku-4-5-20251001",
    "Sonnet-4.6": "claude-sonnet-4-6",
    "Sonnet-5": "claude-sonnet-5",
    "Opus-4.6": "claude-opus-4-6",
    "Opus-4.8": "claude-opus-4-8",
    "Fable-5": "claude-fable-5",
}

EFFORT_MAP = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "extra": "xhigh",
    "extra high": "xhigh",
    "extra-high": "xhigh",
    "max": "max",
}


class CommandResult:
    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def run(
    command: Sequence[str],
    cwd: Optional[Path] = None,
    timeout: int = 60,
    env: Optional[Dict[str, str]] = None,
) -> CommandResult:
    try:
        completed = subprocess.run(
            list(command),
            cwd=str(cwd) if cwd else None,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)
    except FileNotFoundError as exc:
        return CommandResult(127, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return CommandResult(124, stdout, stderr or f"Timed out after {timeout}s")


def normalize_session(value: str) -> str:
    if not re.fullmatch(r"\d{1,2}", value.strip()):
        raise ValueError("session must be a number from 01 through 34")
    number = int(value)
    if not 1 <= number <= 34:
        raise ValueError("session must be a number from 01 through 34")
    return f"{number:02d}"


def _looks_like_workspace(path: Path) -> bool:
    return (
        (path / "CLAUDE.md").is_file()
        and (path / ".ai" / "prompts" / "claude").is_dir()
        and (path / "tools" / "pcb_trace_resistance.py").is_file()
    )


def find_workspace(start: Optional[Path] = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current] + list(current.parents):
        if _looks_like_workspace(candidate):
            return candidate
        nested = candidate / "workspace"
        if _looks_like_workspace(nested):
            return nested.resolve()

    script_path = Path(__file__).resolve()
    fallback = script_path.parents[2]
    if _looks_like_workspace(fallback):
        return fallback
    raise RuntimeError(
        "Cannot locate the PathMiner execution root. Run this command from the "
        "active worktree root or its workspace/ directory."
    )


def find_prompt(workspace: Path, session: str) -> Path:
    matches = sorted(
        (workspace / ".ai" / "prompts" / "claude").glob(
            f"Session_{session}_Claude_*.md"
        )
    )
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one Claude prompt for Session {session}; found {len(matches)}"
        )
    return matches[0]


def prompt_assignment(prompt: Path) -> Dict[str, str]:
    text = prompt.read_text(encoding="utf-8")
    fields = {}
    patterns = {
        "model": r"^- \*\*Recommended model:\*\*\s*(.+?)\s*$",
        "effort": r"^- \*\*Effort:\*\*\s*(.+?)\s*$",
        "wave": r"^- \*\*Parallel wave:\*\*\s*(.+?)\s*$",
        "prerequisites": r"^- \*\*Prerequisite sessions:\*\*\s*(.+?)\s*$",
    }
    for name, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.MULTILINE)
        if not match:
            raise RuntimeError(f"Prompt is missing assignment field: {name}")
        fields[name] = match.group(1).strip()
    fields["model_id"] = MODEL_IDS.get(fields["model"], "")
    fields["cli_effort"] = EFFORT_MAP.get(fields["effort"].lower(), "")
    return fields


def git_value(workspace: Path, *args: str) -> str:
    result = run(["git", "-C", str(workspace), *args], timeout=20)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def git_top(workspace: Path) -> Path:
    return Path(git_value(workspace, "rev-parse", "--show-toplevel")).resolve()


def git_common_root(workspace: Path) -> Path:
    """Return the main checkout root shared by all linked worktrees."""
    common_text = git_value(workspace, "rev-parse", "--git-common-dir")
    common = Path(common_text)
    if not common.is_absolute():
        common = (workspace / common).resolve()
    else:
        common = common.resolve()
    if common.name != ".git":
        raise RuntimeError(f"Unexpected Git common directory: {common}")
    return common.parent


def shared_venv(workspace: Path) -> Path:
    """Return PathMiner's one shared virtual environment directory."""
    return git_common_root(workspace) / ".venv"


def find_python(workspace: Path) -> Path:
    worktree = git_top(workspace)
    candidates = [shared_venv(workspace) / "bin" / "python"]
    active = os.environ.get("VIRTUAL_ENV")
    if active:
        candidates.append(Path(active) / "bin" / "python")
    candidates.extend(
        [
            worktree / ".venv" / "bin" / "python",
            workspace / ".venv" / "bin" / "python",
        ]
    )
    for candidate in candidates:
        if candidate.is_file() and os.access(str(candidate), os.X_OK):
            # Do not call Path.resolve() here. A virtual environment's Python
            # executable is commonly a symlink to the base interpreter. Running
            # the resolved target bypasses pyvenv.cfg and silently drops the
            # virtual environment's site-packages.
            return candidate.absolute()
    return Path(sys.executable).resolve()


def python_environment(workspace: Path) -> Tuple[Path, Dict[str, str]]:
    python = find_python(workspace)
    env = os.environ.copy()
    if python.parent.name == "bin" and python.parent.parent.name == ".venv":
        venv = python.parent.parent
        env["VIRTUAL_ENV"] = str(venv)
        env["PATH"] = str(python.parent) + os.pathsep + env.get("PATH", "")
        env.pop("PYTHONHOME", None)
    return python, env


def status_rows(workspace: Path) -> Dict[int, Dict[str, str]]:
    path = workspace / ".ai" / "coordination" / "SESSION_STATUS.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {int(row["session"]): row for row in csv.DictReader(handle)}


def prerequisite_numbers(assignment: Dict[str, str]) -> List[int]:
    value = assignment["prerequisites"]
    if value.lower() == "none":
        return []
    return [int(item) for item in re.findall(r"Session\s+(\d{1,2})", value)]


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
