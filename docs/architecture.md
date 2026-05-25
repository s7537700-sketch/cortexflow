# CortexFlow Architecture

## Design Philosophy

CortexFlow is built on three principles:

1. **Modular Agents** — each agent is an independent unit with its own model, prompt, and tool configuration. Agents are discoverable and replaceable.
2. **Pipeline DAG** — analysis is expressed as a directed acyclic graph of stages, enabling parallel execution, conditional branching, and automatic recovery.
3. **Interface Diversity** — the platform exposes itself through REST, WebSocket, MCP, CLI, and Web interfaces simultaneously, allowing maximum integration flexibility.

## System Components

### Agent Layer
Each agent implements the `BaseAgent` abstract class with:
- `run(context, pipeline_results)` — core execution method
- `execute(context, pipeline_results)` — wrapper with timing, logging, error handling
- Built-in token estimation and context truncation

### Core Engine
- **Pipeline** — DAG-based executor with topological sorting, parallel groups, and fallback chains
- **Job Queue** — async priority queue with configurable concurrency (default: 10)
- **Token Tracker** — per-agent and aggregate token accounting with monthly budgets

### Interface Layer
All interfaces run concurrently through the same engine instance:
- **FastAPI** on port 8000 — REST + WebSocket + static files
- **MCP Server** on port 9000 or stdio — for IDE integration
- **Web Dashboard** — standalone HTML/JS/CSS or served via API server
- **CLI** — via `core/engine.py` with `make cli`

## Data Flow

```
Client → API/MCP/CLI → Engine → Pipeline (DAG) → Agents → Results
                     ↘ Queue (async) ↗              ↘ Token Tracker
```

## Security Boundaries
- All agent contexts are isolated per session
- Token budgets prevent runaway consumption
- Plugin loading is restricted to `.py` and `.so` extensions
- MCP server operates with local-only permissions by default
