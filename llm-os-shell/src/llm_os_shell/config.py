"""
Configuration management for llm-os-shell.
Loads settings from environment variables and a config file (~/.llm-os-shell.toml).
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

CONFIG_FILE = Path.home() / ".llm-os-shell.toml"
DEFAULT_LOG_DIR = Path.home() / ".llm-os-shell" / "logs"


@dataclass
class ShellConfig:
    llm_backend: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    gpt4all_model_path: str = ""
    openai_base_url: str = "http://localhost:11434/v1"
    openai_api_key: str = "none"
    openai_model: str = "llama3"

    risk_threshold: str = "medium"
    auto_approve_low: bool = True
    require_confirmation_high: bool = True
    require_confirmation_critical: bool = True

    log_enabled: bool = True
    log_dir: str = str(DEFAULT_LOG_DIR)
    log_level: str = "INFO"

    history_file: str = str(Path.home() / ".llm-os-shell" / "history")
    max_history: int = 1000

    llm_timeout: int = 30
    llm_max_tokens: int = 512

    prompt_style: str = "default"
    show_risk_badge: bool = True
    color_enabled: bool = True

    extra_dangerous_patterns: list = field(default_factory=list)
    trusted_commands: list = field(default_factory=list)


def _parse_toml_simple(content: str) -> dict:
    """Very simple TOML parser for flat key=value files."""
    result = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("["):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            else:
                try:
                    value = int(value)
                except ValueError:
                    pass
            result[key] = value
    return result


def load_config() -> ShellConfig:
    config = ShellConfig()

    env_map = {
        "LLM_OS_BACKEND": "llm_backend",
        "LLM_OS_OLLAMA_URL": "ollama_base_url",
        "LLM_OS_OLLAMA_MODEL": "ollama_model",
        "LLM_OS_GPT4ALL_MODEL": "gpt4all_model_path",
        "LLM_OS_RISK_THRESHOLD": "risk_threshold",
        "LLM_OS_LOG_DIR": "log_dir",
        "LLM_OS_LOG_ENABLED": "log_enabled",
        "LLM_OS_COLOR": "color_enabled",
        "LLM_OS_TIMEOUT": "llm_timeout",
    }

    for env_key, attr in env_map.items():
        val = os.environ.get(env_key)
        if val is not None:
            current = getattr(config, attr)
            if isinstance(current, bool):
                setattr(config, attr, val.lower() in ("1", "true", "yes"))
            elif isinstance(current, int):
                try:
                    setattr(config, attr, int(val))
                except ValueError:
                    pass
            else:
                setattr(config, attr, val)

    if CONFIG_FILE.exists():
        try:
            raw = CONFIG_FILE.read_text()
            overrides = _parse_toml_simple(raw)
            for key, value in overrides.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        except Exception:
            pass

    return config


def save_config(config: ShellConfig) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# llm-os-shell configuration\n",
        "# Generated automatically — edit as needed\n\n",
        "[llm]\n",
    ]
    for key, value in asdict(config).items():
        if isinstance(value, list):
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        lines.append(f'{key} = "{value}"\n')
    CONFIG_FILE.write_text("".join(lines))
