"""
Structured logging for all LLM interactions and user decisions.
Logs are stored as JSON-L (one JSON object per line) for easy analysis.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .risk import RiskAssessment, RiskLevel


_COLORS = {
    "DEBUG": "\033[37m",
    "INFO": "\033[36m",
    "WARNING": "\033[33m",
    "ERROR": "\033[91m",
    "CRITICAL": "\033[31m",
}
_RESET = "\033[0m"
_BOLD = "\033[1m"


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = _COLORS.get(record.levelname, "")
        msg = super().format(record)
        return f"{color}{msg}{_RESET}"


def _setup_python_logger(log_dir: str, level: str, color: bool) -> logging.Logger:
    log = logging.getLogger("llm-os-shell")
    log.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not log.handlers:
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(logging.WARNING)
        if color:
            ch.setFormatter(ColorFormatter("%(levelname)s: %(message)s"))
        else:
            ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        log.addHandler(ch)

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_path = Path(log_dir) / "shell.log"
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(fh)

    return log


class InteractionLogger:
    """
    Records every LLM interaction and user decision as JSON-L.
    Each line is a self-contained event record.
    """

    def __init__(self, log_dir: str, enabled: bool = True, color: bool = True, level: str = "INFO"):
        self.enabled = enabled
        self.log_dir = Path(log_dir)
        self._python_log = _setup_python_logger(log_dir, level, color)

        if enabled:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self._jsonl_path = self.log_dir / f"interactions-{today}.jsonl"
        else:
            self._jsonl_path = None

    def _write(self, event: dict) -> None:
        if not self.enabled or self._jsonl_path is None:
            return
        event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        try:
            with open(self._jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError as e:
            self._python_log.warning(f"Failed to write interaction log: {e}")

    def log_command_received(self, command: str, assessment: RiskAssessment) -> None:
        self._write({
            "event": "command_received",
            "command": command,
            "risk_level": assessment.level.value,
            "risk_reasons": assessment.reasons,
            "flags": assessment.flags,
            "requires_llm": assessment.requires_llm,
            "requires_confirmation": assessment.requires_confirmation,
        })

    def log_llm_analysis(self, assessment: RiskAssessment, llm_result: dict, latency_ms: int) -> None:
        self._write({
            "event": "llm_analysis",
            "command": assessment.command,
            "risk_level": assessment.level.value,
            "llm_result": llm_result,
            "latency_ms": latency_ms,
            "backend": llm_result.get("backend", "unknown"),
        })

    def log_user_decision(self, command: str, decision: str, reason: Optional[str] = None) -> None:
        self._write({
            "event": "user_decision",
            "command": command,
            "decision": decision,
            "reason": reason,
        })

    def log_execution(self, command: str, exit_code: int, duration_ms: int) -> None:
        self._write({
            "event": "execution",
            "command": command,
            "exit_code": exit_code,
            "duration_ms": duration_ms,
        })

    def log_error(self, message: str, command: Optional[str] = None) -> None:
        self._python_log.error(message)
        self._write({
            "event": "error",
            "message": message,
            "command": command,
        })

    def info(self, message: str) -> None:
        self._python_log.info(message)

    def warning(self, message: str) -> None:
        self._python_log.warning(message)

    def debug(self, message: str) -> None:
        self._python_log.debug(message)

    @property
    def log_path(self) -> Optional[Path]:
        return self._jsonl_path
