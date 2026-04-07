"""
Risk classification engine.
Analyzes shell commands and assigns a risk level before sending to the LLM.
"""

from __future__ import annotations

import re
import shlex
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class RiskLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


RISK_ORDER = {
    RiskLevel.SAFE: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}

LEVEL_COLORS = {
    RiskLevel.SAFE: "\033[32m",
    RiskLevel.LOW: "\033[36m",
    RiskLevel.MEDIUM: "\033[33m",
    RiskLevel.HIGH: "\033[91m",
    RiskLevel.CRITICAL: "\033[31m",
}
RESET = "\033[0m"
BOLD = "\033[1m"


@dataclass
class RiskAssessment:
    level: RiskLevel
    reasons: list[str]
    command: str
    requires_llm: bool
    requires_confirmation: bool
    flags: list[str]


CRITICAL_PATTERNS = [
    (r"\brm\b.*-[a-zA-Z]*r[a-zA-Z]*f|rm\b.*-[a-zA-Z]*f[a-zA-Z]*r", "Recursive force-remove"),
    (r"\brm\b.*--no-preserve-root", "Removing filesystem root"),
    (r"rm\s+(-[a-zA-Z]*\s+)*(/|/\*)", "Deleting root directory"),
    (r"\bmkfs\b", "Formatting a filesystem"),
    (r"\bdd\s+if=.*of=/dev/", "Writing directly to a block device"),
    (r"\bshred\b", "Secure file wiping"),
    (r":(){ :|:& };:", "Fork bomb"),
    (r"\bcrontab\b.*-r\b", "Removing all cron jobs"),
    (r"chmod\s+(-[a-zA-Z]*\s+)*777\s+/", "Setting world-writable permissions on root"),
    (r"\bsudoers\b", "Modifying sudoers"),
    (r">\s*/etc/passwd", "Overwriting passwd file"),
]

HIGH_PATTERNS = [
    (r"\brm\b.*-[a-zA-Z]*r", "Recursive removal"),
    (r"\brm\b.*-[a-zA-Z]*f", "Force removal"),
    (r"\bsudo\b", "Running with elevated privileges"),
    (r"\bsu\b(\s|$)", "Switching user"),
    (r"\bchmod\b.*7[0-9][0-9]", "Permissive file permissions"),
    (r"\bchown\b.*root", "Changing ownership to root"),
    (r"\bkill\b.*-9", "Force-killing process"),
    (r"\bkillall\b", "Killing all processes by name"),
    (r"\bpkill\b", "Pattern-based process kill"),
    (r"\biptables\b", "Firewall rule modification"),
    (r"\bufw\b", "Firewall configuration"),
    (r"\bsystemctl\b.*(stop|disable|mask)", "Stopping/disabling system service"),
    (r"\bservice\b.*(stop|restart)", "Stopping/restarting service"),
    (r">\s+/etc/", "Overwriting system config file"),
    (r"\bdd\b", "Raw disk copy (dd)"),
    (r"\btar\b.*--overwrite", "Overwriting files with tar"),
    (r"\bcurl\b.*\|\s*(ba)?sh", "Piping URL content into shell"),
    (r"\bwget\b.*\|\s*(ba)?sh", "Piping URL content into shell"),
    (r"\beval\b", "Dynamic code evaluation"),
    (r"\bexec\b", "Process replacement"),
    (r"\bnmap\b", "Network scanning"),
    (r"\bnetcat\b|\bnc\b", "Netcat (potential backdoor)"),
    (r"\bssh\b.*-R\b", "Reverse SSH tunnel"),
]

MEDIUM_PATTERNS = [
    (r"\brm\b", "File removal"),
    (r"\bmv\b", "File move (potential data loss)"),
    (r"\btruncate\b", "File truncation"),
    (r"\bcurl\b", "Network request"),
    (r"\bwget\b", "Network download"),
    (r"\bpip\b.*install", "Installing Python packages"),
    (r"\bnpm\b.*install", "Installing Node packages"),
    (r"\bapt\b.*(install|remove|purge)", "System package management"),
    (r"\byum\b.*(install|remove|erase)", "System package management"),
    (r"\bdnf\b.*(install|remove|erase)", "System package management"),
    (r"\bchmod\b", "Changing file permissions"),
    (r"\bchown\b", "Changing file ownership"),
    (r"\bcrontab\b", "Modifying cron jobs"),
    (r"\bssh\b", "Remote connection"),
    (r"\bscp\b", "Secure copy (network)"),
    (r"\brsync\b", "Remote sync"),
    (r"\btar\b.*-x", "Archive extraction"),
    (r"\bunzip\b", "Archive extraction"),
    (r"\benv\b.*=", "Setting environment variables"),
    (r"\bexport\b", "Exporting environment variable"),
    (r"\bsource\b|\.\s", "Sourcing a script"),
    (r"^\s*\.", "Sourcing a script"),
    (r"\bfind\b.*-delete", "Finding and deleting files"),
    (r"\bxargs\b", "Piping to xargs (bulk execution)"),
    (r"2>&1\s*>\s*/dev/null", "Silencing errors"),
]

LOW_PATTERNS = [
    (r"\bls\b", "Directory listing"),
    (r"\bcat\b", "File read"),
    (r"\becho\b", "Printing text"),
    (r"\bpwd\b", "Print working directory"),
    (r"\bwhoami\b", "Check current user"),
    (r"\bdate\b", "Date/time"),
    (r"\bman\b", "Manual page"),
    (r"\bhelp\b", "Help command"),
    (r"\bhistory\b", "Command history"),
    (r"\buname\b", "System info"),
    (r"\bdf\b", "Disk free"),
    (r"\bdu\b", "Disk usage"),
    (r"\bps\b", "Process list"),
    (r"\bpgrep\b", "Process search"),
    (r"\bgrep\b", "Text search"),
    (r"\bfind\b", "Find files"),
    (r"\bwhich\b|\bwhereis\b", "Find command location"),
    (r"\bhead\b|\btail\b", "File preview"),
    (r"\bwc\b", "Word/line count"),
    (r"\bsort\b", "Sorting"),
    (r"\buniq\b", "Unique filtering"),
    (r"\bawk\b|\bsed\b", "Text processing"),
    (r"\btouch\b", "File creation/update"),
    (r"\bmkdir\b", "Create directory"),
    (r"\bcp\b", "File copy"),
    (r"\bcd\b", "Change directory"),
    (r"\benv\b(?!\s*=)", "List environment"),
    (r"\bprintenv\b", "Print environment"),
]

SAFE_BUILTINS = {
    "ls", "pwd", "echo", "cd", "clear", "exit", "help", "history",
    "whoami", "date", "time", "man", "info", "uname", "hostname",
    "env", "printenv", "which", "type", "alias", "unalias",
}


def _match_patterns(command: str, patterns: list[tuple[str, str]]) -> list[str]:
    reasons = []
    for pattern, reason in patterns:
        if re.search(pattern, command, re.IGNORECASE):
            reasons.append(reason)
    return reasons


def _has_pipe_chain(command: str) -> bool:
    return "|" in command


def _has_redirect_to_system(command: str) -> bool:
    return bool(re.search(r">\s*/etc/|>\s*/usr/|>\s*/bin/|>\s*/sbin/", command))


def _has_glob_root(command: str) -> bool:
    return bool(re.search(r"(/\*|/\.\*|\s/\s)", command))


def assess_risk(command: str, trusted_commands: list[str] | None = None) -> RiskAssessment:
    command = command.strip()
    trusted_commands = trusted_commands or []

    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()

    base_cmd = parts[0] if parts else ""

    if not base_cmd or base_cmd in ("#",):
        return RiskAssessment(
            level=RiskLevel.SAFE,
            reasons=[],
            command=command,
            requires_llm=False,
            requires_confirmation=False,
            flags=[],
        )

    if base_cmd in trusted_commands:
        return RiskAssessment(
            level=RiskLevel.SAFE,
            reasons=["Trusted command"],
            command=command,
            requires_llm=False,
            requires_confirmation=False,
            flags=["trusted"],
        )

    flags = []
    reasons = []
    level = RiskLevel.SAFE

    critical_reasons = _match_patterns(command, CRITICAL_PATTERNS)
    if critical_reasons:
        level = RiskLevel.CRITICAL
        reasons.extend(critical_reasons)
        flags.append("critical_pattern")

    if level != RiskLevel.CRITICAL:
        high_reasons = _match_patterns(command, HIGH_PATTERNS)
        if high_reasons:
            level = RiskLevel.HIGH
            reasons.extend(high_reasons)

    if RISK_ORDER[level] < RISK_ORDER[RiskLevel.HIGH]:
        medium_reasons = _match_patterns(command, MEDIUM_PATTERNS)
        if medium_reasons:
            if RISK_ORDER[level] < RISK_ORDER[RiskLevel.MEDIUM]:
                level = RiskLevel.MEDIUM
            reasons.extend(medium_reasons)

    if RISK_ORDER[level] < RISK_ORDER[RiskLevel.MEDIUM]:
        low_reasons = _match_patterns(command, LOW_PATTERNS)
        if low_reasons:
            if level == RiskLevel.SAFE:
                level = RiskLevel.LOW
            reasons.extend(low_reasons)

    if _has_redirect_to_system(command):
        if RISK_ORDER[level] < RISK_ORDER[RiskLevel.HIGH]:
            level = RiskLevel.HIGH
        reasons.append("Redirecting output to a system directory")
        flags.append("system_redirect")

    if _has_glob_root(command) and RISK_ORDER[level] >= RISK_ORDER[RiskLevel.MEDIUM]:
        level = RiskLevel.CRITICAL
        reasons.append("Glob targeting root filesystem")
        flags.append("root_glob")

    if _has_pipe_chain(command) and RISK_ORDER[level] >= RISK_ORDER[RiskLevel.HIGH]:
        flags.append("pipe_chain")
        reasons.append("Complex pipe chain")

    if not reasons and base_cmd in SAFE_BUILTINS:
        level = RiskLevel.SAFE

    requires_llm = RISK_ORDER[level] >= RISK_ORDER[RiskLevel.MEDIUM]
    requires_confirmation = RISK_ORDER[level] >= RISK_ORDER[RiskLevel.HIGH]

    return RiskAssessment(
        level=level,
        reasons=list(dict.fromkeys(reasons)),
        command=command,
        requires_llm=requires_llm,
        requires_confirmation=requires_confirmation,
        flags=flags,
    )


def risk_badge(level: RiskLevel, color: bool = True) -> str:
    labels = {
        RiskLevel.SAFE: "SAFE",
        RiskLevel.LOW: "LOW",
        RiskLevel.MEDIUM: "MEDIUM",
        RiskLevel.HIGH: "HIGH",
        RiskLevel.CRITICAL: "CRITICAL",
    }
    label = labels[level]
    if not color:
        return f"[{label}]"
    c = LEVEL_COLORS.get(level, "")
    return f"{c}{BOLD}[{label}]{RESET}"
