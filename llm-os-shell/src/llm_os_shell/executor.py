"""
Command executor: runs shell commands as subprocesses.
Handles builtins (cd, exit, etc.) specially.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ExecutionResult:
    command: str
    exit_code: int
    duration_ms: int
    is_builtin: bool
    builtin_handled: bool = False


_BUILTIN_ALIASES = {"quit": "exit", "q": "exit"}

SHELL_BUILTINS = {"cd", "exit", "quit", "q", "help", "history", "alias", "unalias", "export", "set"}


def execute(command: str, env: Optional[dict] = None, aliases: Optional[dict] = None) -> ExecutionResult:
    """Execute a shell command, handling builtins first."""
    command = command.strip()
    if not command or command.startswith("#"):
        return ExecutionResult(command=command, exit_code=0, duration_ms=0, is_builtin=True, builtin_handled=True)

    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()

    if not parts:
        return ExecutionResult(command=command, exit_code=0, duration_ms=0, is_builtin=True, builtin_handled=True)

    cmd = parts[0]
    cmd = _BUILTIN_ALIASES.get(cmd, cmd)
    if aliases:
        cmd = aliases.get(cmd, cmd)

    if cmd == "exit":
        code = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        sys.exit(code)

    if cmd == "cd":
        target = parts[1] if len(parts) > 1 else str(Path.home())
        try:
            os.chdir(os.path.expanduser(os.path.expandvars(target)))
        except FileNotFoundError:
            print(f"cd: no such file or directory: {target}", file=sys.stderr)
            return ExecutionResult(command=command, exit_code=1, duration_ms=0, is_builtin=True)
        except PermissionError:
            print(f"cd: permission denied: {target}", file=sys.stderr)
            return ExecutionResult(command=command, exit_code=1, duration_ms=0, is_builtin=True)
        return ExecutionResult(command=command, exit_code=0, duration_ms=0, is_builtin=True)

    start = time.monotonic()
    try:
        result = subprocess.run(
            command,
            shell=True,
            env={**os.environ, **(env or {})},
            cwd=os.getcwd(),
        )
        exit_code = result.returncode
    except KeyboardInterrupt:
        print()
        exit_code = 130
    except Exception as e:
        print(f"Error executing command: {e}", file=sys.stderr)
        exit_code = 1
    finally:
        duration_ms = int((time.monotonic() - start) * 1000)

    return ExecutionResult(
        command=command,
        exit_code=exit_code,
        duration_ms=duration_ms,
        is_builtin=False,
    )
