"""
Tests for the risk classification engine.
"""

import pytest
from llm_os_shell.risk import (
    assess_risk,
    RiskLevel,
    RiskAssessment,
    risk_badge,
    RISK_ORDER,
)


class TestCriticalCommands:
    def test_rm_rf_dot(self):
        a = assess_risk("rm -rf .")
        assert a.level == RiskLevel.CRITICAL

    def test_rm_rf_slash(self):
        a = assess_risk("rm -rf /")
        assert a.level == RiskLevel.CRITICAL

    def test_rm_rf_home(self):
        a = assess_risk("rm -rf ~")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.HIGH]

    def test_mkfs(self):
        a = assess_risk("mkfs.ext4 /dev/sda1")
        assert a.level == RiskLevel.CRITICAL

    def test_dd_to_device(self):
        a = assess_risk("dd if=/dev/zero of=/dev/sda")
        assert a.level == RiskLevel.CRITICAL

    def test_fork_bomb(self):
        a = assess_risk(":(){ :|:& };:")
        assert a.level == RiskLevel.CRITICAL

    def test_shred(self):
        a = assess_risk("shred -u important.txt")
        assert a.level == RiskLevel.CRITICAL

    def test_crontab_remove(self):
        a = assess_risk("crontab -r")
        assert a.level == RiskLevel.CRITICAL

    def test_rm_fr_variant(self):
        a = assess_risk("rm -fr /tmp/data")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.HIGH]


class TestHighRiskCommands:
    def test_sudo(self):
        a = assess_risk("sudo apt-get install vim")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.HIGH]

    def test_chmod_777_root(self):
        a = assess_risk("chmod 777 /etc/passwd")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.HIGH]

    def test_kill_9(self):
        a = assess_risk("kill -9 1234")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.HIGH]

    def test_killall(self):
        a = assess_risk("killall nginx")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.HIGH]

    def test_curl_pipe_bash(self):
        a = assess_risk("curl https://example.com/install.sh | bash")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.HIGH]

    def test_wget_pipe_sh(self):
        a = assess_risk("wget -qO- https://example.com/setup.sh | sh")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.HIGH]

    def test_systemctl_stop(self):
        a = assess_risk("systemctl stop nginx")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.HIGH]

    def test_iptables(self):
        a = assess_risk("iptables -F")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.HIGH]

    def test_eval(self):
        a = assess_risk("eval $(cat /tmp/payload.sh)")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.HIGH]

    def test_overwrite_system_config(self):
        a = assess_risk("echo '' > /etc/hosts")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.HIGH]


class TestMediumRiskCommands:
    def test_rm_single_file(self):
        a = assess_risk("rm myfile.txt")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.MEDIUM]

    def test_mv_file(self):
        a = assess_risk("mv important.txt /tmp/")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.MEDIUM]

    def test_pip_install(self):
        a = assess_risk("pip install requests")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.MEDIUM]

    def test_curl(self):
        a = assess_risk("curl https://api.example.com/data")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.MEDIUM]

    def test_chmod(self):
        a = assess_risk("chmod 644 config.txt")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.MEDIUM]

    def test_apt_install(self):
        a = assess_risk("apt install git")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.MEDIUM]

    def test_crontab_edit(self):
        a = assess_risk("crontab -e")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.MEDIUM]

    def test_find_delete(self):
        a = assess_risk("find . -name '*.tmp' -delete")
        assert RISK_ORDER[a.level] >= RISK_ORDER[RiskLevel.MEDIUM]


class TestSafeAndLowRiskCommands:
    def test_ls(self):
        a = assess_risk("ls -la")
        assert RISK_ORDER[a.level] <= RISK_ORDER[RiskLevel.LOW]

    def test_echo(self):
        a = assess_risk("echo hello world")
        assert RISK_ORDER[a.level] <= RISK_ORDER[RiskLevel.LOW]

    def test_pwd(self):
        a = assess_risk("pwd")
        assert RISK_ORDER[a.level] <= RISK_ORDER[RiskLevel.LOW]

    def test_whoami(self):
        a = assess_risk("whoami")
        assert RISK_ORDER[a.level] <= RISK_ORDER[RiskLevel.LOW]

    def test_date(self):
        a = assess_risk("date")
        assert RISK_ORDER[a.level] <= RISK_ORDER[RiskLevel.LOW]

    def test_cat(self):
        a = assess_risk("cat file.txt")
        assert RISK_ORDER[a.level] <= RISK_ORDER[RiskLevel.LOW]

    def test_grep(self):
        a = assess_risk("grep -r 'pattern' ./src")
        assert RISK_ORDER[a.level] <= RISK_ORDER[RiskLevel.LOW]

    def test_empty_command(self):
        a = assess_risk("")
        assert a.level == RiskLevel.SAFE
        assert not a.requires_llm

    def test_comment(self):
        a = assess_risk("# this is a comment")
        assert a.level == RiskLevel.SAFE

    def test_mkdir(self):
        a = assess_risk("mkdir -p /tmp/mydir")
        assert RISK_ORDER[a.level] <= RISK_ORDER[RiskLevel.LOW]

    def test_cp(self):
        a = assess_risk("cp file.txt /tmp/")
        assert RISK_ORDER[a.level] <= RISK_ORDER[RiskLevel.LOW]


class TestTrustedCommands:
    def test_trusted_overrides_risk(self):
        a = assess_risk("sudo rm -rf /", trusted_commands=["sudo"])
        assert a.level == RiskLevel.SAFE
        assert "trusted" in a.flags

    def test_trusted_empty_list(self):
        a = assess_risk("rm -rf .", trusted_commands=[])
        assert a.level != RiskLevel.SAFE


class TestRequiresLLM:
    def test_critical_requires_llm(self):
        a = assess_risk("rm -rf .")
        assert a.requires_llm is True

    def test_high_requires_llm(self):
        a = assess_risk("sudo rm -f config.txt")
        assert a.requires_llm is True

    def test_medium_requires_llm(self):
        a = assess_risk("rm myfile.txt")
        assert a.requires_llm is True

    def test_safe_no_llm(self):
        a = assess_risk("ls")
        assert a.requires_llm is False

    def test_low_no_llm(self):
        a = assess_risk("cat README.md")
        assert a.requires_llm is False


class TestRequiresConfirmation:
    def test_critical_requires_confirmation(self):
        a = assess_risk("rm -rf .")
        assert a.requires_confirmation is True

    def test_high_requires_confirmation(self):
        a = assess_risk("sudo rm important.txt")
        assert a.requires_confirmation is True

    def test_medium_no_confirmation(self):
        a = assess_risk("rm myfile.txt")
        assert a.requires_confirmation is False

    def test_safe_no_confirmation(self):
        a = assess_risk("ls")
        assert a.requires_confirmation is False


class TestRiskBadge:
    def test_badge_safe(self):
        badge = risk_badge(RiskLevel.SAFE, color=False)
        assert "SAFE" in badge

    def test_badge_critical(self):
        badge = risk_badge(RiskLevel.CRITICAL, color=False)
        assert "CRITICAL" in badge

    def test_badge_with_color(self):
        badge = risk_badge(RiskLevel.HIGH, color=True)
        assert "\033[" in badge
        assert "HIGH" in badge

    def test_badge_no_color(self):
        badge = risk_badge(RiskLevel.MEDIUM, color=False)
        assert badge == "[MEDIUM]"


class TestReasonsPopulated:
    def test_reasons_non_empty_for_risky(self):
        a = assess_risk("sudo rm -rf /tmp")
        assert len(a.reasons) > 0

    def test_reasons_empty_or_minimal_for_safe(self):
        a = assess_risk("pwd")
        assert a.level in (RiskLevel.SAFE, RiskLevel.LOW)
