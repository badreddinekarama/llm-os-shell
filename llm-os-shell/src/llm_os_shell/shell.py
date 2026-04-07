"""
Main shell loop: the interactive POSIX-compatible shell with LLM safety layer.
"""

from __future__ import annotations

import os
import readline
import sys
import time
from pathlib import Path
from typing import Optional

from .config import ShellConfig, load_config
from .display import Display
from .executor import execute, SHELL_BUILTINS
from .llm_backend import LLMBackend, build_backend
from .logger import InteractionLogger
from .risk import RiskLevel, RiskAssessment, assess_risk, risk_badge, RISK_ORDER


HELP_TEXT = """
llm-os-shell — LLM-powered interactive shell

Built-in commands:
  cd <dir>          Change directory
  exit [code]       Exit the shell
  help              Show this help message
  lls-config        Show current configuration
  lls-log           Show path to interaction log
  lls-backend       Show active LLM backend info
  lls-risks         Show risk assessment for a command (lls-risks <cmd>)
  history           Show command history

Configuration:
  Set environment variables to customize behavior:
    LLM_OS_BACKEND       Backend: ollama | openai-compat | rule-based
    LLM_OS_OLLAMA_URL    Ollama base URL (default: http://localhost:11434)
    LLM_OS_OLLAMA_MODEL  Ollama model name (default: llama3)
    LLM_OS_RISK_THRESHOLD  Minimum risk level for LLM: medium | high | critical
    LLM_OS_LOG_DIR       Log directory
    LLM_OS_COLOR         Enable color: 1 | 0

  Or create ~/.llm-os-shell.toml for persistent settings.

Risk levels:
  SAFE     → Execute without any intervention
  LOW      → Note shown, execute immediately
  MEDIUM   → LLM consulted, executes after analysis
  HIGH     → LLM consulted, confirmation required
  CRITICAL → LLM consulted, must type 'yes' to proceed
"""


def _build_prompt(config: ShellConfig, color: bool) -> str:
    cwd = os.getcwd()
    home = str(Path.home())
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]

    user = os.environ.get("USER", os.environ.get("USERNAME", "user"))

    if color:
        green = "\033[32m"
        cyan = "\033[36m"
        bold = "\033[1m"
        reset = "\033[0m"
        return f"{bold}{green}llm-os{reset}{cyan}:{cwd}{reset}{bold}$ {reset}"
    else:
        return f"llm-os:{cwd}$ "


class Shell:
    def __init__(self, config: Optional[ShellConfig] = None):
        self.config = config or load_config()
        self.display = Display(color=self.config.color_enabled)
        self.logger = InteractionLogger(
            log_dir=self.config.log_dir,
            enabled=self.config.log_enabled,
            color=self.config.color_enabled,
            level=self.config.log_level,
        )
        self.backend: LLMBackend = build_backend(self.config)
        self._aliases: dict[str, str] = {}
        self._setup_readline()
        self.logger.info(f"Shell started with backend: {self.backend.name}")

    def _setup_readline(self) -> None:
        hist = Path(self.config.history_file)
        hist.parent.mkdir(parents=True, exist_ok=True)
        if hist.exists():
            try:
                readline.read_history_file(str(hist))
            except OSError:
                pass
        readline.set_history_length(self.config.max_history)

        try:
            readline.parse_and_bind("tab: complete")
            readline.set_completer_delims(" \t\n;")
        except Exception:
            pass

    def _save_history(self) -> None:
        hist = Path(self.config.history_file)
        try:
            readline.write_history_file(str(hist))
        except OSError:
            pass

    def _handle_builtin(self, command: str) -> Optional[bool]:
        """Handle shell-level builtins. Returns True if handled, None otherwise."""
        parts = command.strip().split(None, 1)
        if not parts:
            return True

        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "help":
            print(HELP_TEXT)
            return True

        if cmd == "lls-config":
            self._show_config()
            return True

        if cmd == "lls-log":
            if self.logger.log_path:
                print(f"Interaction log: {self.logger.log_path}")
            else:
                print("Logging is disabled.")
            return True

        if cmd == "lls-backend":
            print(f"Active backend: {self.backend.name}")
            print(f"Available: {self.backend.is_available()}")
            return True

        if cmd == "lls-risks":
            if args:
                a = assess_risk(args, self.config.trusted_commands)
                print(f"Command: {args}")
                print(f"Risk:    {risk_badge(a.level, self.config.color_enabled)} {a.level.value}")
                print(f"Reasons: {', '.join(a.reasons) or 'none'}")
                print(f"Flags:   {', '.join(a.flags) or 'none'}")
                print(f"LLM?     {a.requires_llm}")
                print(f"Confirm? {a.requires_confirmation}")
            else:
                print("Usage: lls-risks <command>")
            return True

        if cmd == "history":
            n = readline.get_current_history_length()
            for i in range(1, n + 1):
                print(f"  {i:4}  {readline.get_history_item(i)}")
            return True

        return None

    def _show_config(self) -> None:
        cfg = self.config
        print(f"  Backend:         {cfg.llm_backend}")
        print(f"  Active backend:  {self.backend.name}")
        print(f"  Risk threshold:  {cfg.risk_threshold}")
        print(f"  Log enabled:     {cfg.log_enabled}")
        print(f"  Log dir:         {cfg.log_dir}")
        print(f"  Color:           {cfg.color_enabled}")
        print(f"  Auto-approve low:{cfg.auto_approve_low}")

    def _threshold_exceeded(self, assessment: RiskAssessment) -> bool:
        threshold_map = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL,
        }
        threshold = threshold_map.get(self.config.risk_threshold.lower(), RiskLevel.MEDIUM)
        return RISK_ORDER[assessment.level] >= RISK_ORDER[threshold]

    def _consult_llm(self, assessment: RiskAssessment) -> dict:
        cwd = os.getcwd()
        user = os.environ.get("USER", os.environ.get("USERNAME", "user"))

        self.display.thinking_indicator(self.backend.name)
        start = time.monotonic()
        result = self.backend.analyze(assessment, cwd, user)
        latency_ms = int((time.monotonic() - start) * 1000)
        self.display.thinking_done(latency_ms)

        self.logger.log_llm_analysis(assessment, result, latency_ms)
        return result

    def _get_confirmation(self, assessment: RiskAssessment) -> bool:
        """Ask the user whether to proceed. Returns True if they approve."""
        prompt = self.display.confirmation_prompt(assessment)

        while True:
            try:
                answer = input(prompt).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return False

            if assessment.level == RiskLevel.CRITICAL:
                if answer == "yes":
                    self.logger.log_user_decision(assessment.command, "approved", "typed yes")
                    return True
                elif answer in ("no", "n", ""):
                    self.logger.log_user_decision(assessment.command, "rejected", "typed no")
                    return False
                else:
                    print("  Please type 'yes' to confirm or 'no' to cancel.")
            else:
                if answer in ("y", "yes", ""):
                    self.logger.log_user_decision(assessment.command, "approved")
                    return True
                elif answer in ("n", "no"):
                    self.logger.log_user_decision(assessment.command, "rejected")
                    return False
                elif answer == "alt":
                    print("  Run the suggested alternative instead (copy and paste from above).")
                    return False
                else:
                    print("  Please answer y/n.")

    def run_command(self, command: str) -> int:
        """Process and possibly execute a single command. Returns exit code."""
        command = command.strip()
        if not command or command.startswith("#"):
            return 0

        if self._handle_builtin(command) is True:
            return 0

        assessment = assess_risk(command, self.config.trusted_commands)
        self.logger.log_command_received(command, assessment)

        if self.config.show_risk_badge and assessment.level not in (RiskLevel.SAFE,):
            badge = risk_badge(assessment.level, self.config.color_enabled)
            self.display.print_dim(f"  {badge} {assessment.level.value.upper()}: {', '.join(assessment.reasons[:2])}")

        llm_result: Optional[dict] = None

        if assessment.requires_llm and self._threshold_exceeded(assessment):
            llm_result = self._consult_llm(assessment)
            self.display.risk_banner(assessment, llm_result)

            llm_reco = llm_result.get("llm_recommendation", "warn")
            if llm_reco == "block" and assessment.level == RiskLevel.CRITICAL:
                print()
                self.display.print_error("LLM recommends blocking this command.")

        elif assessment.level in (RiskLevel.MEDIUM,) and self._threshold_exceeded(assessment):
            self.display.risk_banner(assessment, None)

        if assessment.requires_confirmation and self._threshold_exceeded(assessment):
            approved = self._get_confirmation(assessment)
            if not approved:
                self.display.abort_indicator()
                return 130
        elif assessment.level == RiskLevel.MEDIUM and self._threshold_exceeded(assessment):
            approved = self._get_confirmation(assessment)
            if not approved:
                self.display.abort_indicator()
                return 130

        result = execute(command, aliases=self._aliases)
        self.logger.log_execution(command, result.exit_code, result.duration_ms)

        return result.exit_code

    def run(self) -> None:
        """Main interactive loop."""
        self._print_banner()

        last_exit = 0

        while True:
            try:
                prompt = _build_prompt(self.config, self.config.color_enabled)
                command = input(prompt).strip()
            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                print()
                self._save_history()
                sys.exit(0)

            if not command:
                continue

            last_exit = self.run_command(command)

    def _print_banner(self) -> None:
        color = self.config.color_enabled
        bold = "\033[1m" if color else ""
        cyan = "\033[36m" if color else ""
        reset = "\033[0m" if color else ""
        dim = "\033[2m" if color else ""

        print(f"{bold}{cyan}llm-os-shell{reset} {dim}v0.1.0 — LLM-powered safe shell{reset}")
        print(f"{dim}Backend: {self.backend.name}  |  Type 'help' for commands  |  Ctrl+D to exit{reset}")
        print()
