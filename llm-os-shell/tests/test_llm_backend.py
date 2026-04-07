"""
Tests for LLM backend abstraction.
"""

import pytest
from unittest.mock import patch, MagicMock
from llm_os_shell.risk import assess_risk, RiskLevel
from llm_os_shell.llm_backend import (
    RuleBasedBackend,
    OllamaBackend,
    OpenAICompatibleBackend,
    build_backend,
)
from llm_os_shell.config import ShellConfig


class TestRuleBasedBackend:
    def setup_method(self):
        self.backend = RuleBasedBackend()

    def test_is_always_available(self):
        assert self.backend.is_available() is True

    def test_name(self):
        assert self.backend.name == "rule-based"

    def test_analyze_critical(self):
        a = assess_risk("rm -rf .")
        result = self.backend.analyze(a, "/home/user", "user")
        assert "explanation" in result
        assert "risks" in result
        assert "safer_alternative" in result
        assert "real_risk" in result
        assert "llm_recommendation" in result
        assert result["backend"] == "rule-based"

    def test_analyze_critical_blocks(self):
        a = assess_risk("rm -rf .")
        result = self.backend.analyze(a, "/", "root")
        assert result["llm_recommendation"] == "block"

    def test_analyze_high_warns(self):
        a = assess_risk("sudo apt remove git")
        result = self.backend.analyze(a, "/home/user", "user")
        assert result["llm_recommendation"] in ("warn", "block")

    def test_analyze_safe_proceeds(self):
        a = assess_risk("ls -la")
        result = self.backend.analyze(a, "/home/user", "user")
        assert result["llm_recommendation"] == "proceed"

    def test_explanation_is_string(self):
        a = assess_risk("rm important.doc")
        result = self.backend.analyze(a, "/home/user", "user")
        assert isinstance(result["explanation"], str)
        assert len(result["explanation"]) > 0

    def test_risks_is_list(self):
        a = assess_risk("sudo rm -rf /tmp")
        result = self.backend.analyze(a, "/", "root")
        assert isinstance(result["risks"], list)

    def test_real_risk_is_valid(self):
        valid_levels = {l.value for l in RiskLevel}
        a = assess_risk("mv /etc/hosts /etc/hosts.bak")
        result = self.backend.analyze(a, "/", "root")
        assert result["real_risk"] in valid_levels

    def test_no_exception_for_empty_command(self):
        a = assess_risk("")
        result = self.backend.analyze(a, "/", "user")
        assert "explanation" in result


class TestOllamaBackendUnavailable:
    def test_unavailable_when_no_server(self):
        b = OllamaBackend(base_url="http://localhost:19999", model="test")
        assert b.is_available() is False

    def test_name_contains_model(self):
        b = OllamaBackend(model="llama3")
        assert "llama3" in b.name

    def test_analyze_falls_back_when_unavailable(self):
        b = OllamaBackend(base_url="http://localhost:19999", model="test", timeout=1)
        a = assess_risk("rm -rf .")
        result = b.analyze(a, "/", "user")
        assert "explanation" in result
        assert "fallback" in result.get("backend", "")


class TestOpenAICompatBackend:
    def test_unavailable_when_no_server(self):
        b = OpenAICompatibleBackend(base_url="http://localhost:19998")
        assert b.is_available() is False

    def test_name_contains_model(self):
        b = OpenAICompatibleBackend(base_url="http://localhost:11434/v1", model="mistral")
        assert "mistral" in b.name

    def test_analyze_falls_back_when_unavailable(self):
        b = OpenAICompatibleBackend(base_url="http://localhost:19998", timeout=1)
        a = assess_risk("rm myfile.txt")
        result = b.analyze(a, "/tmp", "user")
        assert "explanation" in result


class TestBuildBackend:
    def test_rule_based_explicit(self):
        cfg = ShellConfig(llm_backend="rule-based")
        b = build_backend(cfg)
        assert b.name == "rule-based"

    def test_none_backend(self):
        cfg = ShellConfig(llm_backend="none")
        b = build_backend(cfg)
        assert b.name == "rule-based"

    def test_unknown_backend_falls_back(self):
        cfg = ShellConfig(llm_backend="nonexistent-backend-xyz")
        b = build_backend(cfg)
        assert b.name == "rule-based"

    def test_ollama_falls_back_if_unavailable(self):
        cfg = ShellConfig(llm_backend="ollama", ollama_base_url="http://localhost:19999")
        b = build_backend(cfg)
        assert b.name == "rule-based"

    def test_openai_compat_falls_back_if_unavailable(self):
        cfg = ShellConfig(llm_backend="openai-compat", openai_base_url="http://localhost:19998")
        b = build_backend(cfg)
        assert b.name == "rule-based"
