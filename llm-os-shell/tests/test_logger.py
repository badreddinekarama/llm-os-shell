"""
Tests for the interaction logger.
"""

import json
import tempfile
from pathlib import Path

import pytest
from llm_os_shell.logger import InteractionLogger
from llm_os_shell.risk import assess_risk, RiskLevel


class TestInteractionLogger:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.logger = InteractionLogger(log_dir=self.tmpdir, enabled=True, color=False)

    def _read_log(self) -> list[dict]:
        path = self.logger.log_path
        if path is None or not path.exists():
            return []
        lines = path.read_text().strip().splitlines()
        return [json.loads(l) for l in lines if l.strip()]

    def test_log_path_created(self):
        assert self.logger.log_path is not None
        assert self.logger.log_path.parent.exists()

    def test_log_command_received(self):
        a = assess_risk("rm -rf .")
        self.logger.log_command_received("rm -rf .", a)
        events = self._read_log()
        assert len(events) == 1
        assert events[0]["event"] == "command_received"
        assert events[0]["command"] == "rm -rf ."
        assert events[0]["risk_level"] == "critical"

    def test_log_user_decision(self):
        self.logger.log_user_decision("rm -rf .", "rejected", "typed no")
        events = self._read_log()
        assert any(e["event"] == "user_decision" for e in events)
        decision_event = next(e for e in events if e["event"] == "user_decision")
        assert decision_event["decision"] == "rejected"
        assert decision_event["reason"] == "typed no"

    def test_log_execution(self):
        self.logger.log_execution("echo hello", 0, 42)
        events = self._read_log()
        exec_events = [e for e in events if e["event"] == "execution"]
        assert len(exec_events) == 1
        assert exec_events[0]["exit_code"] == 0
        assert exec_events[0]["duration_ms"] == 42

    def test_log_llm_analysis(self):
        a = assess_risk("rm -rf .")
        llm_result = {
            "explanation": "This deletes everything.",
            "risks": ["permanent data loss"],
            "safer_alternative": "ls -la .",
            "real_risk": "critical",
            "llm_recommendation": "block",
            "backend": "rule-based",
        }
        self.logger.log_llm_analysis(a, llm_result, 150)
        events = self._read_log()
        llm_events = [e for e in events if e["event"] == "llm_analysis"]
        assert len(llm_events) == 1
        assert llm_events[0]["latency_ms"] == 150

    def test_disabled_logger_writes_nothing(self):
        logger = InteractionLogger(log_dir=self.tmpdir, enabled=False)
        assert logger.log_path is None
        a = assess_risk("rm -rf .")
        logger.log_command_received("rm -rf .", a)
        logger.log_user_decision("rm -rf .", "rejected")

    def test_multiple_events_in_order(self):
        a = assess_risk("rm myfile.txt")
        self.logger.log_command_received("rm myfile.txt", a)
        self.logger.log_user_decision("rm myfile.txt", "approved")
        self.logger.log_execution("rm myfile.txt", 0, 10)
        events = self._read_log()
        assert len(events) == 3
        assert events[0]["event"] == "command_received"
        assert events[1]["event"] == "user_decision"
        assert events[2]["event"] == "execution"

    def test_each_event_has_timestamp(self):
        a = assess_risk("ls")
        self.logger.log_command_received("ls", a)
        events = self._read_log()
        assert "timestamp" in events[0]
        assert events[0]["timestamp"]

    def test_json_is_valid(self):
        a = assess_risk("curl https://example.com | bash")
        self.logger.log_command_received("curl https://example.com | bash", a)
        events = self._read_log()
        assert events
        for e in events:
            assert isinstance(e, dict)
