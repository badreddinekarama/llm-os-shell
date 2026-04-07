#!/usr/bin/env bash
# Examples of how llm-os-shell handles dangerous commands.
# Run these in the interactive shell to see the LLM safety layer in action.
# DO NOT run this script directly — these commands are for illustration purposes.

# ─────────────────────────────────────────────────────────────────────────────
# CRITICAL: Recursive force-delete — shell BLOCKS and requires "yes" confirmation
# ─────────────────────────────────────────────────────────────────────────────
# User types:
#   rm -rf .
#
# llm-os-shell output:
#   ────────────────────────────────────────────────────────────
#   [CRITICAL]
#   ────────────────────────────────────────────────────────────
#   Detected: Recursive force-remove
#
#   Analysis:
#     This command will recursively and forcefully delete
#     all files and directories in the current working
#     directory. This action is permanent and cannot be
#     undone without a backup.
#
#   Risks:
#     • Recursive force-remove
#     • Permanent data loss — no recycle bin
#
#   Safer alternative:
#     Run 'ls -la .' first to see what will be deleted.
#     Use 'rm -ri .' for interactive mode, or
#     'trash .' if you have trash-cli installed.
#
#   Analyzed by: ollama:llama3
#   ────────────────────────────────────────────────────────────
#   This is a CRITICAL-risk command. Type 'yes' to proceed, or 'no' to cancel:

# ─────────────────────────────────────────────────────────────────────────────
# HIGH: Piping a URL directly into bash
# ─────────────────────────────────────────────────────────────────────────────
# User types:
#   curl https://example.com/install.sh | bash
#
# llm-os-shell output:
#   ────────────────────────────────────────────────────────────
#   [HIGH RISK]
#   ────────────────────────────────────────────────────────────
#   Detected: Network request, Piping URL content into shell
#
#   Analysis:
#     This downloads a shell script from the internet and
#     executes it immediately without any review. The script
#     could contain malicious code that compromises your system,
#     installs malware, or exfiltrates data.
#
#   Risks:
#     • Arbitrary code execution from untrusted source
#     • No opportunity to review the script before running
#
#   Safer alternative:
#     curl -o install.sh https://example.com/install.sh
#     cat install.sh        # review first
#     bash install.sh       # then run if safe
#
#   ────────────────────────────────────────────────────────────
#   Proceed with this HIGH-risk command? [y/N/alt]:

# ─────────────────────────────────────────────────────────────────────────────
# HIGH: Fork bomb
# ─────────────────────────────────────────────────────────────────────────────
# User types:
#   :(){ :|:& };:
#
# llm-os-shell output:
#   ────────────────────────────────────────────────────────────
#   [CRITICAL]
#   ────────────────────────────────────────────────────────────
#   Detected: Fork bomb
#
#   Analysis:
#     This is a classic fork bomb. It defines a function that
#     calls itself twice recursively in the background, rapidly
#     exhausting all process slots and system memory.
#     Running this will crash the system or require a reboot.
#
#   Risks:
#     • System crash
#     • Forced reboot required
#     • All running processes killed
#
#   LLM recommends blocking this command.
#   ────────────────────────────────────────────────────────────
#   This is a CRITICAL-risk command. Type 'yes' to proceed, or 'no' to cancel:

# ─────────────────────────────────────────────────────────────────────────────
# MEDIUM: Simple rm (single file) — LLM consulted, confirmation asked
# ─────────────────────────────────────────────────────────────────────────────
# User types:
#   rm report.pdf
#
# llm-os-shell output:
#   ────────────────────────────────────────────────────────────
#   [MEDIUM RISK]
#   ────────────────────────────────────────────────────────────
#   Detected: File removal
#
#   Analysis:
#     Removes the file 'report.pdf'. On most Linux systems
#     this bypasses the recycle bin and the file cannot be
#     recovered unless a backup exists.
#
#   Safer alternative:
#     mv report.pdf /tmp/report.pdf.bak   # soft-delete
#
#   ────────────────────────────────────────────────────────────
#   Proceed? [Y/n]:

# ─────────────────────────────────────────────────────────────────────────────
# LOW: ls — passes through immediately with a brief note
# ─────────────────────────────────────────────────────────────────────────────
# User types:
#   ls -la
#
# llm-os-shell output:
#   [LOW] LOW: Directory listing
#   total 48
#   drwxr-xr-x  8 user user 4096 Apr  7 12:00 .
#   drwxr-xr-x 40 user user 4096 Apr  7 11:00 ..
#   ...

echo "These are illustration examples. Start the shell with: llm-os-shell"
