# Workspace

## Overview

pnpm workspace monorepo using TypeScript. Also contains the **llm-os-shell** open-source Python project in the `llm-os-shell/` directory.

## llm-os-shell (Python project)

A POSIX-compatible interactive shell with LLM-powered safety analysis.

### Structure
```
llm-os-shell/
├── src/llm_os_shell/    # Core Python package
├── tests/               # 138-test pytest suite
├── examples/            # Usage examples and config reference
├── pyproject.toml       # Package metadata
├── README.md            # Full documentation
└── LICENSE              # MIT
```

### Key commands (run from llm-os-shell/)
- `python -m llm_os_shell` — start interactive shell
- `python -m llm_os_shell --backend rule-based` — no LLM needed
- `python -m llm_os_shell -c "rm -rf ."` — single command mode
- `python -m pytest tests/ -v` — run all tests

### Modules
- `risk.py` — 50+ pattern risk classifier (safe/low/medium/high/critical)
- `llm_backend.py` — pluggable LLM backends (Ollama, OpenAI-compat, rule-based)
- `shell.py` — interactive shell loop with confirmation flow
- `executor.py` — subprocess executor with builtin handling
- `display.py` — terminal color output and risk banners
- `logger.py` — JSON-L structured interaction logging
- `config.py` — env var + TOML config loading

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.
