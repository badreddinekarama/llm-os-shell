"""
LLM backend abstraction layer.
Supports: Ollama (default), OpenAI-compatible APIs, GPT4All, and a rule-based fallback.
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Optional

from .risk import RiskAssessment, RiskLevel, RISK_ORDER


ANALYSIS_PROMPT_TEMPLATE = """You are a shell command safety analyst. A user is about to run the following command:

  {command}

Risk classification: {risk_level}
Risk reasons: {risk_reasons}
Current directory: {cwd}
User: {user}

Your task:
1. Explain in 2-4 sentences what this command does and what its consequences are.
2. Identify any destructive, irreversible, or dangerous effects.
3. Suggest a safer alternative if one exists.
4. Rate the real risk: safe / low / medium / high / critical.

Respond in this JSON format:
{{
  "explanation": "...",
  "risks": ["..."],
  "safer_alternative": "...",
  "real_risk": "medium",
  "llm_recommendation": "proceed | warn | block"
}}

Be concise. No markdown. Just JSON.
"""


class LLMBackend(ABC):
    @abstractmethod
    def analyze(self, assessment: RiskAssessment, cwd: str, user: str) -> dict:
        """Analyze a command and return a structured response."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    def is_available(self) -> bool:
        return True


class RuleBasedBackend(LLMBackend):
    """
    Fallback backend when no LLM is available.
    Uses static rules to generate explanations.
    """

    @property
    def name(self) -> str:
        return "rule-based"

    def is_available(self) -> bool:
        return True

    def analyze(self, assessment: RiskAssessment, cwd: str, user: str) -> dict:
        cmd = assessment.command
        level = assessment.level
        reasons = assessment.reasons

        explanation_map = {
            "Recursive force-remove": (
                f"This command will recursively and forcefully delete files/directories "
                f"matching the pattern in '{cmd}'. This action is irreversible."
            ),
            "Recursive removal": (
                f"This command will recursively remove a directory and all its contents. "
                f"Files deleted this way cannot be easily recovered."
            ),
            "Force removal": (
                f"The -f flag suppresses confirmation prompts. "
                f"Files will be deleted without asking again."
            ),
            "Running with elevated privileges": (
                f"This command runs with root privileges, giving it full system access."
            ),
            "File removal": (
                f"This command removes a file from the filesystem. "
                f"Recovery may not be possible without a backup."
            ),
            "File move (potential data loss)": (
                f"This moves or renames a file. If the destination exists, it may be overwritten."
            ),
            "Formatting a filesystem": (
                f"This command formats a storage device, erasing ALL data on it permanently."
            ),
        }

        explanation = "This command performs the following action(s): " + "; ".join(reasons) + "."
        for key, msg in explanation_map.items():
            if key in reasons:
                explanation = msg
                break

        risks = [r for r in reasons if r != "Trusted command"]

        safer_map = {
            RiskLevel.CRITICAL: f"Consider checking the path carefully before executing. Use 'ls' to preview what will be affected.",
            RiskLevel.HIGH: f"Consider using 'echo {cmd}' first to preview, or add '-i' for interactive confirmation.",
            RiskLevel.MEDIUM: f"Review the target paths before running this command.",
            RiskLevel.LOW: "Command appears relatively safe.",
            RiskLevel.SAFE: "No safer alternative needed.",
        }

        recommendation_map = {
            RiskLevel.CRITICAL: "block",
            RiskLevel.HIGH: "warn",
            RiskLevel.MEDIUM: "warn",
            RiskLevel.LOW: "proceed",
            RiskLevel.SAFE: "proceed",
        }

        return {
            "explanation": explanation,
            "risks": risks,
            "safer_alternative": safer_map.get(level, ""),
            "real_risk": level.value,
            "llm_recommendation": recommendation_map.get(level, "warn"),
            "backend": self.name,
        }


class OllamaBackend(LLMBackend):
    """Backend using a local Ollama instance."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    @property
    def name(self) -> str:
        return f"ollama:{self.model}"

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def analyze(self, assessment: RiskAssessment, cwd: str, user: str) -> dict:
        import os
        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            command=assessment.command,
            risk_level=assessment.level.value,
            risk_reasons=", ".join(assessment.reasons) if assessment.reasons else "none",
            cwd=cwd,
            user=user,
        )

        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_predict": 512},
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
                raw = data.get("response", "{}")
                result = json.loads(raw)
                result["backend"] = self.name
                return result
        except json.JSONDecodeError as e:
            return self._fallback(assessment, f"LLM returned invalid JSON: {e}")
        except urllib.error.URLError as e:
            return self._fallback(assessment, f"Ollama unreachable: {e}")
        except Exception as e:
            return self._fallback(assessment, str(e))

    def _fallback(self, assessment: RiskAssessment, error: str) -> dict:
        fb = RuleBasedBackend()
        result = fb.analyze(assessment, "", "")
        result["backend"] = f"{self.name}(fallback:{error[:60]})"
        return result


class OpenAICompatibleBackend(LLMBackend):
    """Backend for any OpenAI-compatible endpoint (LM Studio, llama.cpp, etc.)."""

    def __init__(self, base_url: str, api_key: str = "none", model: str = "local", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @property
    def name(self) -> str:
        return f"openai-compat:{self.model}"

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def analyze(self, assessment: RiskAssessment, cwd: str, user: str) -> dict:
        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            command=assessment.command,
            risk_level=assessment.level.value,
            risk_reasons=", ".join(assessment.reasons) if assessment.reasons else "none",
            cwd=cwd,
            user=user,
        )

        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 512,
            "response_format": {"type": "json_object"},
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
                raw = data["choices"][0]["message"]["content"]
                result = json.loads(raw)
                result["backend"] = self.name
                return result
        except Exception as e:
            fb = RuleBasedBackend()
            result = fb.analyze(assessment, cwd, user)
            result["backend"] = f"{self.name}(fallback:{str(e)[:60]})"
            return result


def build_backend(config) -> LLMBackend:
    """Construct the appropriate LLM backend from config."""
    backend_name = config.llm_backend.lower()

    if backend_name == "ollama":
        b = OllamaBackend(
            base_url=config.ollama_base_url,
            model=config.ollama_model,
            timeout=config.llm_timeout,
        )
        if b.is_available():
            return b
        return RuleBasedBackend()

    elif backend_name in ("openai", "openai-compat", "lmstudio", "llama-cpp"):
        b = OpenAICompatibleBackend(
            base_url=config.openai_base_url,
            api_key=config.openai_api_key,
            model=config.openai_model,
            timeout=config.llm_timeout,
        )
        if b.is_available():
            return b
        return RuleBasedBackend()

    elif backend_name == "none" or backend_name == "rule-based":
        return RuleBasedBackend()

    else:
        return RuleBasedBackend()
