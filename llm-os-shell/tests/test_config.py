"""
Tests for configuration loading.
"""

import os
import pytest
from unittest.mock import patch
from llm_os_shell.config import ShellConfig, load_config


class TestDefaultConfig:
    def test_default_backend(self):
        cfg = ShellConfig()
        assert cfg.llm_backend == "ollama"

    def test_default_risk_threshold(self):
        cfg = ShellConfig()
        assert cfg.risk_threshold == "medium"

    def test_default_log_enabled(self):
        cfg = ShellConfig()
        assert cfg.log_enabled is True

    def test_default_color_enabled(self):
        cfg = ShellConfig()
        assert cfg.color_enabled is True

    def test_default_auto_approve_low(self):
        cfg = ShellConfig()
        assert cfg.auto_approve_low is True

    def test_default_model(self):
        cfg = ShellConfig()
        assert cfg.ollama_model == "llama3"

    def test_trusted_commands_empty(self):
        cfg = ShellConfig()
        assert cfg.trusted_commands == []


class TestEnvOverrides:
    def test_backend_env(self):
        with patch.dict(os.environ, {"LLM_OS_BACKEND": "rule-based"}):
            cfg = load_config()
            assert cfg.llm_backend == "rule-based"

    def test_threshold_env(self):
        with patch.dict(os.environ, {"LLM_OS_RISK_THRESHOLD": "high"}):
            cfg = load_config()
            assert cfg.risk_threshold == "high"

    def test_color_disabled_env(self):
        with patch.dict(os.environ, {"LLM_OS_COLOR": "0"}):
            cfg = load_config()
            assert cfg.color_enabled is False

    def test_color_enabled_env(self):
        with patch.dict(os.environ, {"LLM_OS_COLOR": "1"}):
            cfg = load_config()
            assert cfg.color_enabled is True

    def test_log_enabled_false(self):
        with patch.dict(os.environ, {"LLM_OS_LOG_ENABLED": "false"}):
            cfg = load_config()
            assert cfg.log_enabled is False

    def test_ollama_url_env(self):
        with patch.dict(os.environ, {"LLM_OS_OLLAMA_URL": "http://myserver:11434"}):
            cfg = load_config()
            assert cfg.ollama_base_url == "http://myserver:11434"

    def test_timeout_env(self):
        with patch.dict(os.environ, {"LLM_OS_TIMEOUT": "60"}):
            cfg = load_config()
            assert cfg.llm_timeout == 60
