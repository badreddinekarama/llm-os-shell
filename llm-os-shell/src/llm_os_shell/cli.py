"""
CLI entry point with argument parsing.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import load_config
from .shell import Shell


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="llm-os-shell",
        description="A POSIX-compatible interactive shell with LLM-powered safety analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  llm-os-shell                    Start the interactive shell
  llm-os-shell -c "rm -rf /tmp/x" Run a single command
  llm-os-shell --backend rule-based  Use built-in rules without LLM
  llm-os-shell --threshold high   Only consult LLM for HIGH+ risk commands

Environment variables:
  LLM_OS_BACKEND        ollama | openai-compat | rule-based
  LLM_OS_OLLAMA_URL     Ollama URL (default: http://localhost:11434)
  LLM_OS_OLLAMA_MODEL   Ollama model (default: llama3)
  LLM_OS_RISK_THRESHOLD medium | high | critical
  LLM_OS_LOG_DIR        Directory for interaction logs
  LLM_OS_COLOR          1 to enable color, 0 to disable
""",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("-c", "--command", metavar="CMD", help="Execute a single command and exit")
    p.add_argument(
        "--backend",
        choices=["ollama", "openai-compat", "rule-based"],
        help="LLM backend to use",
    )
    p.add_argument(
        "--threshold",
        choices=["low", "medium", "high", "critical"],
        help="Minimum risk level that triggers LLM analysis",
    )
    p.add_argument("--no-color", action="store_true", help="Disable color output")
    p.add_argument("--no-log", action="store_true", help="Disable interaction logging")
    p.add_argument(
        "--model",
        metavar="MODEL",
        help="Model name for the selected backend (e.g. llama3, mistral)",
    )
    p.add_argument(
        "--ollama-url",
        metavar="URL",
        help="Ollama base URL (default: http://localhost:11434)",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config()

    if args.backend:
        config.llm_backend = args.backend
    if args.threshold:
        config.risk_threshold = args.threshold
    if args.no_color:
        config.color_enabled = False
    if args.no_log:
        config.log_enabled = False
    if args.model:
        config.ollama_model = args.model
        config.openai_model = args.model
    if args.ollama_url:
        config.ollama_base_url = args.ollama_url

    shell = Shell(config=config)

    if args.command:
        exit_code = shell.run_command(args.command)
        sys.exit(exit_code)
    else:
        shell.run()


if __name__ == "__main__":
    main()
