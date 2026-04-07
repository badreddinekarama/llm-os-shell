"""
Terminal display utilities: colored output, risk banners, LLM explanations.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from .risk import RiskLevel, RiskAssessment, LEVEL_COLORS, RESET, BOLD

_GREEN = "\033[32m"
_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_RED = "\033[91m"
_DIM = "\033[2m"
_ITALIC = "\033[3m"
_UNDERLINE = "\033[4m"


def _supports_color() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


class Display:
    def __init__(self, color: bool = True):
        self.color = color and _supports_color()

    def _c(self, code: str) -> str:
        return code if self.color else ""

    def _reset(self) -> str:
        return RESET if self.color else ""

    def risk_banner(self, assessment: RiskAssessment, llm_result: Optional[dict] = None) -> None:
        level = assessment.level
        color = LEVEL_COLORS.get(level, "") if self.color else ""
        reset = self._reset()
        bold = BOLD if self.color else ""

        level_labels = {
            RiskLevel.SAFE: "SAFE",
            RiskLevel.LOW: "LOW RISK",
            RiskLevel.MEDIUM: "MEDIUM RISK",
            RiskLevel.HIGH: "HIGH RISK",
            RiskLevel.CRITICAL: "CRITICAL RISK",
        }

        label = level_labels[level]

        print()
        print(f"{color}{bold}{'─' * 60}{reset}")
        print(f"{color}{bold}  {label}{reset}")
        print(f"{color}{bold}{'─' * 60}{reset}")

        if assessment.reasons:
            print(f"  {self._c(_DIM)}Detected: {', '.join(assessment.reasons[:3])}{reset}")

        if llm_result:
            explanation = llm_result.get("explanation", "")
            if explanation:
                print()
                print(f"  {self._c(_CYAN)}{bold}Analysis:{reset}")
                for line in _wrap(explanation, 56):
                    print(f"    {line}")

            risks = llm_result.get("risks", [])
            if risks:
                print()
                print(f"  {self._c(_YELLOW)}{bold}Risks:{reset}")
                for r in risks[:4]:
                    print(f"    {self._c(_YELLOW)}•{reset} {r}")

            alt = llm_result.get("safer_alternative", "")
            if alt and alt.lower() not in ("", "none", "no safer alternative needed."):
                print()
                print(f"  {self._c(_GREEN)}{bold}Safer alternative:{reset}")
                for line in _wrap(alt, 56):
                    print(f"    {self._c(_GREEN)}{line}{reset}")

            backend = llm_result.get("backend", "")
            if backend:
                print()
                print(f"  {self._c(_DIM)}Analyzed by: {backend}{reset}")

        print(f"{color}{bold}{'─' * 60}{reset}")

    def confirmation_prompt(self, assessment: RiskAssessment) -> str:
        level = assessment.level
        color = LEVEL_COLORS.get(level, "") if self.color else ""
        reset = self._reset()
        bold = BOLD if self.color else ""

        if level == RiskLevel.CRITICAL:
            prompt = f"{color}{bold}  This is a CRITICAL-risk command. Type 'yes' to proceed, or 'no' to cancel: {reset}"
        elif level == RiskLevel.HIGH:
            prompt = f"{color}{bold}  Proceed with this HIGH-risk command? [y/N/alt]: {reset}"
        else:
            prompt = f"{color}  Proceed? [Y/n]: {reset}"

        return prompt

    def print_info(self, message: str) -> None:
        print(f"{self._c(_CYAN)}{message}{self._reset()}")

    def print_success(self, message: str) -> None:
        print(f"{self._c(_GREEN)}{message}{self._reset()}")

    def print_warning(self, message: str) -> None:
        print(f"{self._c(_YELLOW)}{BOLD if self.color else ''}Warning: {message}{self._reset()}", file=sys.stderr)

    def print_error(self, message: str) -> None:
        print(f"{self._c(_RED)}{BOLD if self.color else ''}Error: {message}{self._reset()}", file=sys.stderr)

    def print_dim(self, message: str) -> None:
        print(f"{self._c(_DIM)}{message}{self._reset()}")

    def thinking_indicator(self, backend_name: str) -> None:
        print(f"  {self._c(_DIM)}Consulting LLM ({backend_name})...{self._reset()}", end="", flush=True)

    def thinking_done(self, latency_ms: int) -> None:
        print(f"\r  {self._c(_DIM)}Analysis complete ({latency_ms}ms)                      {self._reset()}")

    def abort_indicator(self) -> None:
        print(f"\n  {self._c(_RED)}{BOLD if self.color else ''}Command aborted.{self._reset()}")

    def execution_indicator(self, command: str) -> None:
        dim = self._c(_DIM)
        reset = self._reset()
        print(f"  {dim}$ {command}{reset}")


def _wrap(text: str, width: int) -> list[str]:
    """Simple word wrap."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= width:
            current = (current + " " + word).lstrip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]
