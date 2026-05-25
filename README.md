<div align="center">
  <h1>🧠 CortexFlow</h1>
  <p><strong>Multi-Agent AI Orchestration Platform</strong></p>
  <p>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT"></a>
    <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
    <img src="https://img.shields.io/badge/agents-7-orange" alt="7 Agents">
    <img src="https://img.shields.io/badge/API-FastAPI-green" alt="FastAPI">
    <img src="https://img.shields.io/badge/MCP-Protocol-purple" alt="MCP Protocol">
    <img src="https://img.shields.io/badge/tokens%2Fjob-%7E500K-blueviolet" alt="~500K tokens/job">
  </p>
</div>

---

**CortexFlow** is a production-grade multi-agent AI orchestration platform for automated security analysis, code review, and vulnerability research. It provides a complete ecosystem: **7 specialized AI agents**, a **REST API server**, a **web dashboard**, **MCP protocol support** for IDE integration, and **Docker deployment** — all working together as a unified platform.

Unlike single-agent tools, CortexFlow chains multiple agents in configurable pipelines, tracks every token consumed, provides real-time monitoring via WebSocket, and exposes itself as tools for Claude Code, OpenCode, and Cursor through the MCP protocol.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        CortexFlow Platform                        │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Agent Layer (7 agents)                 │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │   │
│  │  │Orchestr. │ │Code      │ │Vuln      │ │Exploit     │  │   │
│  │  │Agent     │ │Analyzer  │ │Scanner   │ │Suggester  │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                 │   │
│  │  │Report    │ │Config    │ │Monitor   │                 │   │
│  │  │Generator │ │Extractor │ │Agent     │                 │   │
│  │  └──────────┘ └──────────┘ └──────────┘                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Core Engine Layer                            │   │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │   │
│  │  │Pipeline │ │Job Queue │ │Token     │ │Plugin        │ │   │
│  │  │Engine   │ │Manager   │ │Tracker   │ │Manager       │ │   │
│  │  └─────────┘ └──────────┘ └──────────┘ └──────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Interface Layer                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │   │
│  │  │REST API  │ │WebSocket│ │Web       │ │MCP Server  │  │   │
│  │  │FastAPI   │ │Streaming│ │Dashboard │ │(IDE Tools) │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

## 🤖 Agent Catalog

| Agent | Model | Role | Token Budget |
|---|---|---|---|
| **Orchestrator** | Claude Sonnet 4.5 | Pipeline planner, coordinator, dynamic pipeline design | 48K |
| **Code Analyzer** | Claude Sonnet 4.5 | Static code analysis, vulnerability patterns, complexity metrics | 24K |
| **Vuln Scanner** | Claude Sonnet 4.5 | Automated vulnerability discovery, CWE classification, risk scoring | 32K |
| **Exploit Suggester** | Claude Opus 4.5 | Exploit strategy, payload templates, tool recommendations | 32K |
| **Report Generator** | Claude Haiku 4.5 | Report synthesis, YARA/Snort rules, executive summaries | 16K |
| **Config Extractor** | Claude Haiku 4.5 | Configuration analysis, secret detection, hardcoded credentials | 12K |
| **Monitor** | Claude Haiku 4.5 | Real-time progress, health checks, alert generation | 8K |

## ✨ Features

### Core Platform
- **7 specialized agents** in a pipeline DAG architecture
- **FastAPI REST API** with WebSocket real-time updates
- **MCP Protocol Server** — integrate with Claude Code, OpenCode, Cursor
- **Web Dashboard** — real-time monitoring, token analytics, agent management
- **Async Job Queue** — priority scheduling, concurrent execution, progress tracking

### Agent Pipeline
- **Dynamic pipeline planning** — Orchestrator designs optimal agent chain per input
- **Sequential, parallel, and conditional execution** policies
- **Automatic retry** with fallback agents on timeout/failure
- **Dependency resolution** between stages (DAG execution)

### Token Management
- **Per-agent and aggregate token tracking**
- **Monthly budget enforcement** with configurable alerts
- **Cost estimation** at $/1M tokens for budget planning
- **Exportable token reports** with per-session breakdowns

### Developer Experience
- **Docker Compose** — one-command deployment (API + Web + MCP)
- **MCP integration** — use CortexFlow tools directly from your AI coding agent
- **Plugin system** — extend with custom agents and tools
- **CLI interface** — `make dev`, `make cli`, `make mcp` for development

---

## 🚀 Quick Start

### Prerequisites
```bash
python 3.11+
docker & docker-compose (optional)
```

### Installation
```bash
# Clone and install
git clone https://github.com/s7537700-sketch/cortexflow.git
cd cortexflow
pip install -r requirements.txt

# Start API server
make dev
```

### Web Dashboard
```bash
# Open in browser
open http://localhost:8000

# Or serve static dashboard separately
make web
# Then open http://localhost:3000
```

### Docker Deployment
```bash
make docker
# API: http://localhost:8000
# Web: http://localhost:3000
# MCP: localhost:9000
```

---

## 🔧 Usage Examples

### API: Submit Analysis
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "type": "codebase",
    "target": "my-project",
    "content": "YOUR_SOURCE_CODE",
    "pipeline": "default",
    "priority": 5
  }'
```

### API: Check Job Status
```bash
curl http://localhost:8000/api/v1/jobs/<job_id>
```

### MCP: Claude Code Integration
```json
// Add to your Claude Code MCP config:
{
  "mcpServers": {
    "cortexflow": {
      "command": "python",
      "args": ["mcp/server.py"],
      "env": {}
    }
  }
}
```

### Monitor Token Usage
```bash
curl http://localhost:8000/api/v1/tokens
```

---

## 📊 Token Consumption

| Pipeline Mode | Prompt | Completion | Total | Use Case |
|---|---|---|---|---|
| Quick scan | ~60K | ~12K | ~72K | Initial triage |
| Standard analysis | ~120K | ~25K | ~145K | Code review |
| Deep analysis | ~250K | ~50K | ~300K | Vulnerability research |
| Full exploit pipeline | ~400K | ~80K | ~480K | Red team assessment |
| Monthly (100 jobs) | ~12M | ~2.5M | ~14.5M | Team usage |

---

## 📁 Project Structure

```
cortexflow/
├── agents/
│   ├── base_agent.py        # Abstract agent interface
│   ├── orchestrator.py      # Pipeline planner & coordinator
│   ├── code_analyzer.py     # Static code analysis
│   ├── vuln_scanner.py      # Vulnerability discovery
│   ├── exploit_suggester.py # Exploit strategy
│   ├── report_generator.py  # Report synthesis
│   ├── config_extractor.py  # Configuration analysis
│   └── monitor_agent.py     # Health & monitoring
├── core/
│   ├── engine.py            # Main execution runtime
│   ├── pipeline.py          # DAG pipeline executor
│   ├── queue.py             # Async job scheduler
│   └── token_tracker.py     # Token accounting system
├── api/
│   ├── server.py            # FastAPI REST server
│   └── routes.py            # API endpoints
├── mcp/
│   └── server.py            # MCP protocol server
├── web/
│   ├── index.html           # Dashboard entry
│   ├── css/style.css        # Dashboard styles
│   └── js/
│       ├── api.js           # API client
│       └── dashboard.js     # Dashboard app
├── storage/
│   └── database.py          # SQLite persistence
├── config/
│   └── config.yaml          # Platform configuration
├── tests/                   # Test suite
├── docs/
│   ├── architecture.md      # Architecture docs
│   └── api.md               # API documentation
├── Dockerfile               # Container image
├── docker-compose.yml       # Multi-service deployment
├── Makefile                 # Development commands
└── requirements.txt         # Python dependencies
```

---

## 🤝 MCP Protocol Integration

CortexFlow implements the Model Context Protocol, allowing any MCP-compatible client to use its agents as tools:

### Available Tools
| Tool | Description |
|---|---|
| `cortexflow_analyze` | Submit full pipeline analysis job |
| `cortexflow_scan_code` | Quick vulnerability scan of code |
| `cortexflow_get_agents` | List available agents |
| `cortexflow_get_report` | Retrieve analysis results |

### Claude Code / OpenCode Integration
```bash
# In your project directory, add to .mcp.json:
{
  "mcpServers": {
    "cortexflow": {
      "command": "python",
      "args": ["path/to/cortexflow/mcp/server.py"]
    }
  }
}
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <p><strong>7 agents · REST API · Web Dashboard · MCP Protocol · Docker · ~500K tokens/job</strong></p>
  <p>Built for security researchers, by security researchers.</p>
</div>
