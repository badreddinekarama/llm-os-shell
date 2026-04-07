"""
Tests for the command executor.
"""

import os
import sys
import pytest
from unittest.mock import patch
from llm_os_shell.executor import execute, ExecutionResult


class TestBasicExecution:
    def test_echo_command(self):
        result = execute("echo hello")
        assert result.exit_code == 0
        assert result.is_builtin is False

    def test_true_command(self):
        result = execute("true")
        assert result.exit_code == 0

    def test_false_command(self):
        result = execute("false")
        assert result.exit_code != 0

    def test_empty_command(self):
        result = execute("")
        assert result.exit_code == 0
        assert result.is_builtin is True
        assert result.builtin_handled is True

    def test_comment_command(self):
        result = execute("# this is a comment")
        assert result.exit_code == 0
        assert result.is_builtin is True

    def test_whitespace_only(self):
        result = execute("   ")
        assert result.exit_code == 0
        assert result.is_builtin is True

    def test_duration_measured(self):
        result = execute("echo hi")
        assert result.duration_ms >= 0

    def test_nonexistent_command(self):
        result = execute("nonexistent_command_xyz_12345")
        assert result.exit_code != 0


class TestBuiltinCd:
    def test_cd_home(self):
        original = os.getcwd()
        try:
            result = execute("cd ~")
            assert result.exit_code == 0
            assert result.is_builtin is True
        finally:
            os.chdir(original)

    def test_cd_tmp(self):
        original = os.getcwd()
        try:
            result = execute("cd /tmp")
            assert result.exit_code == 0
            assert os.getcwd() == "/tmp"
        finally:
            os.chdir(original)

    def test_cd_nonexistent(self):
        result = execute("cd /nonexistent_path_xyz_12345")
        assert result.exit_code == 1
        assert result.is_builtin is True

    def test_cd_no_args_goes_home(self):
        original = os.getcwd()
        try:
            result = execute("cd")
            assert result.exit_code == 0
            assert os.getcwd() == os.path.expanduser("~")
        finally:
            os.chdir(original)


class TestPipelineCommands:
    def test_pipe_echo_grep(self):
        result = execute("echo hello | grep hello")
        assert result.exit_code == 0

    def test_pipe_no_match(self):
        result = execute("echo hello | grep nonexistent_xyz")
        assert result.exit_code != 0

    def test_semicolon_chaining(self):
        result = execute("echo a; echo b")
        assert result.exit_code == 0


class TestRedirection:
    def test_redirect_to_dev_null(self):
        result = execute("echo hello > /dev/null")
        assert result.exit_code == 0

    def test_redirect_input(self):
        result = execute("cat /dev/null")
        assert result.exit_code == 0


class TestExecutionResult:
    def test_result_fields(self):
        result = execute("echo test")
        assert isinstance(result.exit_code, int)
        assert isinstance(result.duration_ms, int)
        assert isinstance(result.is_builtin, bool)
        assert isinstance(result.command, str)
