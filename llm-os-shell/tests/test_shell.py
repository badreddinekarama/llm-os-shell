"""
Integration tests for the Shell class.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from llm_os_shell.config import ShellConfig
from llm_os_shell.shell import Shell
from llm_os_shell.risk import RiskLevel


def make_shell(threshold="high", log=False) -> Shell:
    """Create a test shell with no real logging and rule-based backend."""
    cfg = ShellConfig(
        llm_backend="rule-based",
        risk_threshold=threshold,
        log_enabled=log,
        color_enabled=False,
        auto_approve_low=True,
    )
    return Shell(config=cfg)


class TestSafeCommandsPassThrough:
    def test_echo_runs(self):
        shell = make_shell()
        code = shell.run_command("echo hello_test_output")
        assert code == 0

    def test_ls_runs(self):
        shell = make_shell()
        code = shell.run_command("ls /tmp")
        assert code == 0

    def test_empty_command(self):
        shell = make_shell()
        code = shell.run_command("")
        assert code == 0

    def test_comment_skipped(self):
        shell = make_shell()
        code = shell.run_command("# just a comment")
        assert code == 0

    def test_true_command(self):
        shell = make_shell()
        code = shell.run_command("true")
        assert code == 0

    def test_false_command(self):
        shell = make_shell()
        code = shell.run_command("false")
        assert code != 0


class TestBuiltinHandlers:
    def test_help_builtin(self, capsys):
        shell = make_shell()
        result = shell._handle_builtin("help")
        out = capsys.readouterr().out
        assert result is True
        assert "llm-os-shell" in out

    def test_lls_config_builtin(self, capsys):
        shell = make_shell()
        result = shell._handle_builtin("lls-config")
        out = capsys.readouterr().out
        assert result is True
        assert "Backend" in out

    def test_lls_backend_builtin(self, capsys):
        shell = make_shell()
        result = shell._handle_builtin("lls-backend")
        out = capsys.readouterr().out
        assert result is True
        assert "rule-based" in out

    def test_lls_risks_builtin(self, capsys):
        shell = make_shell()
        result = shell._handle_builtin("lls-risks rm -rf .")
        out = capsys.readouterr().out
        assert result is True
        assert "CRITICAL" in out.upper() or "HIGH" in out.upper()

    def test_lls_risks_no_args(self, capsys):
        shell = make_shell()
        result = shell._handle_builtin("lls-risks")
        out = capsys.readouterr().out
        assert result is True
        assert "Usage" in out

    def test_lls_log_disabled(self, capsys):
        shell = make_shell(log=False)
        result = shell._handle_builtin("lls-log")
        out = capsys.readouterr().out
        assert result is True
        assert "disabled" in out.lower()

    def test_unknown_builtin_returns_none(self):
        shell = make_shell()
        result = shell._handle_builtin("ls -la")
        assert result is None

    def test_history_builtin(self, capsys):
        shell = make_shell()
        result = shell._handle_builtin("history")
        assert result is True


class TestRiskThreshold:
    def test_threshold_critical_skips_medium_llm(self):
        cfg = ShellConfig(
            llm_backend="rule-based",
            risk_threshold="critical",
            log_enabled=False,
            color_enabled=False,
        )
        shell = Shell(config=cfg)
        assessment_rm = __import__("llm_os_shell.risk", fromlist=["assess_risk"]).assess_risk("rm myfile.txt")
        assert not shell._threshold_exceeded(assessment_rm)

    def test_threshold_medium_includes_medium(self):
        cfg = ShellConfig(
            llm_backend="rule-based",
            risk_threshold="medium",
            log_enabled=False,
            color_enabled=False,
        )
        shell = Shell(config=cfg)
        assessment_rm = __import__("llm_os_shell.risk", fromlist=["assess_risk"]).assess_risk("rm myfile.txt")
        assert shell._threshold_exceeded(assessment_rm)

    def test_threshold_high_skips_medium(self):
        cfg = ShellConfig(
            llm_backend="rule-based",
            risk_threshold="high",
            log_enabled=False,
            color_enabled=False,
        )
        shell = Shell(config=cfg)
        from llm_os_shell.risk import assess_risk
        a = assess_risk("rm myfile.txt")
        assert not shell._threshold_exceeded(a)


class TestConfirmationFlow:
    def test_critical_command_rejected(self, monkeypatch):
        shell = make_shell(threshold="medium")
        monkeypatch.setattr("builtins.input", lambda _: "no")
        code = shell.run_command("rm -rf .")
        assert code == 130

    def test_critical_command_approved_with_yes(self, monkeypatch):
        shell = make_shell(threshold="medium")
        responses = iter(["yes"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        code = shell.run_command("rm -rf /nonexistent_path_xyz_test_only")
        assert code != 130

    def test_high_command_rejected(self, monkeypatch):
        shell = make_shell(threshold="medium")
        monkeypatch.setattr("builtins.input", lambda _: "n")
        code = shell.run_command("sudo echo test")
        assert code == 130

    def test_high_command_approved(self, monkeypatch):
        shell = make_shell(threshold="medium")
        monkeypatch.setattr("builtins.input", lambda _: "y")
        code = shell.run_command("sudo echo test")
        assert isinstance(code, int)
