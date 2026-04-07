<div align="center">

```
██╗     ██╗     ███╗   ███╗       ██████╗ ███████╗    ███████╗██╗  ██╗███████╗██╗     ██╗
██║     ██║     ████╗ ████║      ██╔═══██╗██╔════╝    ██╔════╝██║  ██║██╔════╝██║     ██║
██║     ██║     ██╔████╔██║      ██║   ██║███████╗    ███████╗███████║█████╗  ██║     ██║
██║     ██║     ██║╚██╔╝██║      ██║   ██║╚════██║    ╚════██║██╔══██║██╔══╝  ██║     ██║
███████╗███████╗██║ ╚═╝ ██║      ╚██████╔╝███████║    ███████║██║  ██║███████╗███████╗███████╗
╚══════╝╚══════╝╚═╝     ╚═╝       ╚═════╝ ╚══════╝    ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝
```

**A POSIX-compatible interactive shell with a local LLM as its safety kernel.**  
Every dangerous command is intercepted, explained, and confirmed before it runs.

<br/>

[![CI](https://github.com/badreddinkarama/llm-os-shell/actions/workflows/ci.yml/badge.svg)](https://github.com/badreddinkarama/llm-os-shell/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3b82f6?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![No Cloud](https://img.shields.io/badge/Cloud-None-f59e0b?style=flat-square&logo=cloudflare&logoColor=white)](https://ollama.com)
[![Tests](https://img.shields.io/badge/Tests-138%20passing-22c55e?style=flat-square)](tests/)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero%20(stdlib%20only)-a855f7?style=flat-square)](pyproject.toml)

<br/>

[**Quick Start**](#-quick-start) · [**How It Works**](#-how-it-works) · [**Configuration**](#-configuration) · [**Backends**](#-llm-backends) · [**Contributing**](#-contributing)

</div>

---

## What is llm-os-shell?

`llm-os-shell` wraps your shell commands in an **intelligent safety layer**. Before any risky command executes, a local LLM analyzes it, explains the consequences in plain English, and — depending on severity — requires your explicit confirmation.

It is a **real shell**, not a chatbot. Pipes, redirects, environment variables, history, tab completion — everything works. The LLM is invisible for safe commands and only steps in when it matters.

> **Fully local. Zero cloud. Zero API keys. Zero telemetry.**

---

## Demo

```
llm-os:~$ rm -rf .

  ────────────────────────────────────────────────────────────
  [CRITICAL]
  ────────────────────────────────────────────────────────────
  Detected: Recursive force-remove

  Analysis:
    This command will recursively and forcefully delete all files
    and directories in the current working directory. This action
    is permanent and cannot be undone without a backup.

  Risks:
    • Recursive force-remove
    • Permanent data loss — no recycle bin or undo

  Safer alternative:
    Run 'ls -la .' first to preview what will be deleted.
    Use 'rm -ri .' for interactive confirmation per file.

  Analyzed by: ollama:llama3
  ────────────────────────────────────────────────────────────
  This is a CRITICAL-risk command. Type 'yes' to proceed, or 'no' to cancel: no

  Command aborted.
```

```
llm-os:~$ curl https://example.com/install.sh | bash

  [HIGH RISK] Running with elevated network input, Piping URL content into shell

  Analysis:
    Downloads and immediately executes a remote shell script with no
    opportunity to inspect its contents. The script could install malware,
    exfiltrate data, or modify system files.

  Safer alternative:
    curl -o install.sh https://example.com/install.sh
    cat install.sh   # review it first
    bash install.sh  # then run if safe

  Proceed with this HIGH-risk command? [y/N]: n

  Command aborted.
```

```
llm-os:~$ ls -la
  [LOW] Directory listing
total 64
drwxr-xr-x  8 user user 4096 Apr  7 12:00 .
drwxr-xr-x 40 user user 4096 Apr  7 11:00 ..
-rw-r--r--  1 user user  342 Apr  7 10:45 README.md
```

---

## Features

| | Feature | Details |
|---|---|---|
| **Shell** | Full POSIX compatibility | Pipes, redirects, semicolons, builtins, history, tab completion |
| **Risk Engine** | 50+ detection patterns | 5 levels: `SAFE` → `LOW` → `MEDIUM` → `HIGH` → `CRITICAL` |
| **LLM Layer** | Pluggable backends | Ollama, OpenAI-compatible APIs, built-in rule-based fallback |
| **Logging** | Structured audit trail | Every interaction stored as JSON-L with timestamps |
| **Config** | Flexible | Env vars + `~/.llm-os-shell.toml` config file |
| **Privacy** | 100% local | No cloud, no API keys, no external calls |
| **Speed** | Instant fallback | If LLM is unavailable, built-in rules kick in immediately |

---

## How It Works

```
  You type a command
         │
         ▼
  ┌─────────────────┐
  │   Risk Engine   │  ← 50+ pattern rules classify the command
  └────────┬────────┘
           │
      ┌────┴─────┐
      │          │
    SAFE/LOW   MEDIUM / HIGH / CRITICAL
      │          │
      │          ▼
      │   ┌──────────────┐
      │   │  LLM Backend │  ← Ollama / OpenAI-compat / rule-based
      │   └──────┬───────┘
      │          │
      │          ▼
      │   ┌──────────────┐
      │   │  User Prompt │  ← Explanation + confirmation
      │   └──────┬───────┘
      │          │
      └────►  Execute  ◄──── Approved
                │
                ▼
          JSON-L Log
```

### Risk Levels

| Level | Trigger Examples | LLM? | Needs Confirmation? |
|:---:|---|:---:|:---:|
| `SAFE` | `ls`, `pwd`, `whoami`, `date` | — | — |
| `LOW` | `cat`, `cp`, `mkdir`, `grep` | — | — |
| `MEDIUM` | `rm file`, `mv`, `curl`, `pip install` | ✓ | ✓ `y/n` |
| `HIGH` | `sudo`, `kill -9`, pipe-to-bash, `iptables` | ✓ | ✓ `y/n` |
| `CRITICAL` | `rm -rf`, `mkfs`, fork bomb, `dd if=/dev/zero` | ✓ | ✓ must type **`yes`** |

---

## Quick Start

### Prerequisites

- Python **3.10+**
- No Python package dependencies (pure stdlib)
- Optional: [Ollama](https://ollama.com) for full LLM analysis

### Install

```bash
git clone https://github.com/badreddinkarama/llm-os-shell
cd llm-os-shell
pip install -e .
```

### Run — without an LLM (instant, no setup)

Uses built-in rule-based analysis. Works everywhere, zero configuration.

```bash
llm-os-shell --backend rule-based

# or use the short alias
lls --backend rule-based
```

### Run — with Ollama (recommended)

```bash
# 1. Install Ollama → https://ollama.com
ollama pull llama3
ollama serve              # start server (separate terminal)

# 2. Start the shell — auto-detects Ollama
llm-os-shell
```

### Run — with LM Studio or llama.cpp

```bash
llm-os-shell --backend openai-compat --ollama-url http://localhost:1234/v1 --model your-model
```

### Single command (non-interactive)

```bash
llm-os-shell -c "rm -rf /tmp/old-build"
```

---

## CLI Reference

```
Usage: llm-os-shell [OPTIONS]

Options:
  --version               Show version and exit
  -c, --command CMD       Execute a single command and exit
  --backend BACKEND       Backend: ollama | openai-compat | rule-based
  --threshold LEVEL       Min risk that triggers LLM: low | medium | high | critical
  --model MODEL           Model name (llama3, mistral, codellama, phi3:mini …)
  --ollama-url URL        Ollama base URL  [default: http://localhost:11434]
  --no-color              Disable color output
  --no-log                Disable interaction logging
  -h, --help              Show this message and exit
```

### Built-in Shell Commands

| Command | Description |
|---|---|
| `help` | Show help and available commands |
| `lls-config` | Print active configuration |
| `lls-backend` | Show which LLM backend is active and reachable |
| `lls-risks <cmd>` | Preview risk level for any command before running it |
| `lls-log` | Show path to today's interaction log |
| `history` | Show command history |
| `cd`, `exit` | Standard POSIX builtins |

---

## LLM Backends

Three backends ship out of the box. Swap them with `--backend` or via config.

| Backend | Flag | When to use |
|---|---|---|
| **Ollama** | `ollama` | Local Ollama server. Best quality. Auto-detected. |
| **OpenAI-compatible** | `openai-compat` | LM Studio, llama.cpp server, Kobold, Oobabooga |
| **Rule-based** | `rule-based` | No LLM needed. Instant. Always available as fallback. |

> If the configured LLM backend is unreachable at startup, the shell automatically falls back to rule-based mode — you are never left without protection.

### Adding a Custom Backend

```python
# src/llm_os_shell/llm_backend.py
from llm_os_shell.llm_backend import LLMBackend
from llm_os_shell.risk import RiskAssessment

class MyBackend(LLMBackend):
    @property
    def name(self) -> str:
        return "my-backend"

    def is_available(self) -> bool:
        return True  # health-check your service

    def analyze(self, assessment: RiskAssessment, cwd: str, user: str) -> dict:
        return {
            "explanation": "What this command does...",
            "risks": ["list of risks"],
            "safer_alternative": "a safer way to do it",
            "real_risk": "high",                         # safe|low|medium|high|critical
            "llm_recommendation": "warn",                # proceed|warn|block
            "backend": self.name,
        }
```

Then add your backend name to `build_backend()` in the same file.

---

## Configuration

### Environment Variables

```bash
LLM_OS_BACKEND=ollama            # ollama | openai-compat | rule-based
LLM_OS_OLLAMA_URL=http://localhost:11434
LLM_OS_OLLAMA_MODEL=llama3
LLM_OS_RISK_THRESHOLD=medium     # low | medium | high | critical
LLM_OS_LOG_DIR=~/.llm-os-shell/logs
LLM_OS_LOG_ENABLED=1             # 1 | 0
LLM_OS_COLOR=1                   # 1 | 0
LLM_OS_TIMEOUT=30                # seconds
```

### Config File

Create `~/.llm-os-shell.toml` for persistent settings:

```toml
llm_backend       = "ollama"
ollama_model      = "llama3"
risk_threshold    = "medium"
log_enabled       = "true"
color_enabled     = "true"
llm_timeout       = "30"
```

See [`examples/config_example.toml`](examples/config_example.toml) for the full reference.

---

## Interaction Logs

Every LLM consultation and user decision is persisted as **JSON-L** at:

```
~/.llm-os-shell/logs/interactions-YYYY-MM-DD.jsonl
```

Each line is a self-contained event:

```jsonc
// Command arrives
{"event":"command_received","command":"rm -rf .","risk_level":"critical","risk_reasons":["Recursive force-remove"],"timestamp":"2024-04-07T10:23:45Z"}

// LLM responds
{"event":"llm_analysis","command":"rm -rf .","latency_ms":842,"backend":"ollama:llama3","llm_result":{"real_risk":"critical","llm_recommendation":"block"},"timestamp":"2024-04-07T10:23:46Z"}

// User decides
{"event":"user_decision","command":"rm -rf .","decision":"rejected","reason":"typed no","timestamp":"2024-04-07T10:23:48Z"}
```

<details>
<summary>Event types reference</summary>

| Event | When emitted |
|---|---|
| `command_received` | Every command entered |
| `llm_analysis` | After LLM responds (includes latency) |
| `user_decision` | When user approves or rejects |
| `execution` | After command runs (includes exit code + duration) |
| `error` | On internal errors |

</details>

---

## Recommended Models

Any model that follows JSON instructions works. Tested and recommended:

| Model | Pull Command | Speed | Quality |
|---|---|:---:|:---:|
| Llama 3 8B | `ollama pull llama3` | Fast | ⭐⭐⭐⭐⭐ |
| Mistral 7B | `ollama pull mistral` | Fast | ⭐⭐⭐⭐ |
| CodeLlama | `ollama pull codellama` | Medium | ⭐⭐⭐⭐ |
| Phi-3 Mini | `ollama pull phi3:mini` | Very fast | ⭐⭐⭐ |
| Gemma 2B | `ollama pull gemma:2b` | Very fast | ⭐⭐ |

---

## Project Structure

```
llm-os-shell/
├── src/
│   └── llm_os_shell/
│       ├── __init__.py        # Version, author metadata
│       ├── __main__.py        # python -m llm_os_shell entry point
│       ├── cli.py             # Argument parser + CLI entry
│       ├── shell.py           # Main interactive loop
│       ├── risk.py            # Risk classification engine (50+ patterns)
│       ├── llm_backend.py     # Pluggable backend abstraction
│       ├── executor.py        # Subprocess executor + builtins
│       ├── display.py         # Terminal color + risk banners
│       ├── logger.py          # JSON-L structured logger
│       └── config.py          # Env var + TOML config loader
│
├── tests/
│   ├── test_risk.py           # 50+ risk classification cases
│   ├── test_llm_backend.py    # Backend availability + fallback
│   ├── test_executor.py       # Execution, builtins, pipelines
│   ├── test_config.py         # Config loading + env overrides
│   ├── test_shell.py          # Shell integration + confirmation flow
│   └── test_logger.py         # Structured logging correctness
│
├── examples/
│   ├── dangerous_commands.sh  # Annotated real-world examples
│   └── config_example.toml   # Full config reference
│
├── .github/
│   └── workflows/ci.yml       # GitHub Actions — Python 3.10/3.11/3.12
│
├── pyproject.toml             # Package metadata (PEP 517)
├── LICENSE                    # MIT
└── README.md
```

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

```bash
# with coverage report
pytest tests/ --cov=llm_os_shell --cov-report=term-missing
```

**138 tests** covering:

- Risk classification across all 5 levels (50+ cases)
- Backend availability detection and graceful fallback
- Command execution: builtins, pipelines, redirects, exit codes
- Configuration loading and environment variable overrides
- Shell confirmation flow (approve / reject / threshold gating)
- Structured JSON-L logging correctness and ordering

---

## Security Notes

> [!WARNING]
> `llm-os-shell` is a **safety aid**, not a security boundary.

- Commands execute with your user's privileges — the same as a regular shell.
- The LLM is **advisory only** — final decisions are always yours.
- The risk classifier uses heuristics and may miss novel or obfuscated patterns.
- Interaction logs may contain sensitive command strings — store them securely.
- Never rely on this as your sole protection in production or multi-user systems.

---

## Contributing

Contributions are welcome. Please follow these steps:

1. Fork the repo and create a branch: `git checkout -b feature/my-feature`
2. Make your changes and add tests for new behavior
3. Ensure the full test suite passes: `pytest tests/ -v`
4. Open a pull request with a clear description

**Ideas for contribution:**

- Additional risk patterns (Windows / PowerShell support)
- GPT4All native backend integration
- Plugin system for custom risk analyzers
- Interactive shell completion improvements
- Web UI for browsing interaction logs
- `--dry-run` mode (show analysis but never execute)

---

## Author

<div align="center">

**Badreddine karama**

[![GitHub](https://img.shields.io/badge/GitHub-badreddinkarama-181717?style=for-the-badge&logo=github)](https://github.com/badreddinkarama)

</div>

---

## License

<div align="center">

Released under the **MIT License** — see [LICENSE](LICENSE) for details.

Free to use, modify, and distribute. Attribution appreciated.

</div>
