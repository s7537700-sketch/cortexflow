<div align="center">
  <h1>🧠 CortexFlow</h1>
  <p><strong>Multi-Agent AI Orchestration Platform for Security Analysis</strong></p>
  <p><em>Production-grade • 10 specialized agents • 5 LLM providers • Workflow YAML • Plugin system</em></p>
  <p>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT"></a>
    <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
    <img src="https://img.shields.io/badge/agents-10-orange" alt="10 Agents">
    <img src="https://img.shields.io/badge/providers-5-purple" alt="5 LLM Providers">
    <img src="https://img.shields.io/badge/API-FastAPI-green" alt="FastAPI">
    <img src="https://img.shields.io/badge/MCP-Protocol-purple" alt="MCP Protocol">
    <img src="https://img.shields.io/badge/CLI-Typer-blueviolet" alt="CLI Typer">
    <img src="https://img.shields.io/badge/auth-JWT%20%2B%20RBAC-red" alt="Auth">
    <img src="https://img.shields.io/badge/db-SQLAlchemy-yellow" alt="DB">
  </p>
</div>

---

**CortexFlow** is a production-grade multi-agent AI orchestration platform purpose-built for automated security analysis, code review, malware analysis, and threat hunting. Unlike single-agent tools, CortexFlow chains **10 specialized AI agents** in configurable pipelines, supports **5 different LLM providers** (Anthropic, OpenAI, Google, Xiaomi MiMo, local Ollama), persists every analysis to **SQLAlchemy storage**, exposes itself through **REST API + MCP protocol + CLI + Web Dashboard**, and lets you extend it with **YAML workflows** and **dynamic plugins**.

---

## 🎯 What's New in v2.0

| Feature | v1.0 | v2.0 |
|---|---|---|
| **Specialized agents** | 5 | **10** |
| **LLM providers** | Anthropic only | **5** (Anthropic, OpenAI, Google, MiMo, Ollama) |
| **Workflow templates** | Hardcoded | **YAML-based** (4 templates included) |
| **Database** | None | **SQLAlchemy** (sessions, audit, tokens, users) |
| **Authentication** | None | **JWT + API keys + RBAC** |
| **Plugin system** | None | **Dynamic loading** with manifest.yaml |
| **CLI** | None | **Typer-based** with rich formatting |
| **Tests** | None | **pytest suite** with fixtures |
| **CI/CD** | None | **GitHub Actions** (test + Docker + security) |
| **Lines of code** | ~2,400 | **~8,500+** |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CortexFlow Platform v2.0                      │
├─────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                   Agent Layer (10 specialized)                  │ │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐  │ │
│  │  │Orchestrator│ │CodeAnalyzer│ │VulnScanner │ │ExploitSugg.│  │ │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘  │ │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐  │ │
│  │  │ReportGen   │ │ConfigExtr. │ │  Monitor   │ │NetworkAnal.│  │ │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘  │ │
│  │  ┌────────────┐ ┌────────────┐                                 │ │
│  │  │MemoryForens│ │ThreatIntel │                                 │ │
│  │  └────────────┘ └────────────┘                                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │              Provider Layer (5 LLM providers)                   │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────┐ ┌─────────┐ │ │
│  │  │Anthropic │ │  OpenAI  │ │ Google   │ │ MiMo │ │ Ollama  │ │ │
│  │  │ Claude   │ │ GPT-4o   │ │  Gemini  │ │V2.5  │ │ (local) │ │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────┘ └─────────┘ │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │              Core Engine                                        │ │
│  │  Pipeline DAG • Job Queue • Token Tracker • Plugin Manager     │ │
│  │  Workflow YAML Engine • Event Bus • Cost Estimator             │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │           Storage Layer (SQLAlchemy)                            │ │
│  │  Users • API Keys • Sessions • PipelineRuns • TokenUsage       │ │
│  │  AuditLog • Reports                                             │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │           Interface Layer                                       │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ ┌─────────┐│ │
│  │  │REST API  │ │WebSocket │ │   CLI    │ │  MCP   │ │  Web    ││ │
│  │  │ FastAPI  │ │ Streaming│ │  Typer   │ │ Server │ │Dashboard││ │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘ └─────────┘│ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## 🤖 Agent Catalog (10 specialized agents)

| Agent | Recommended Model | Role | Tokens/Run |
|---|---|---|---|
| **Orchestrator** | Claude Sonnet 4.5 / MiMo V2.5-Pro | Plans pipelines, allocates resources | 18-32K |
| **CodeAnalyzer** | Claude Sonnet 4.5 / GPT-4o | Static analysis, vulnerability patterns | 22-32K |
| **VulnScanner** | Claude Sonnet 4.5 / MiMo V2.5 | Auto vulnerability discovery, CWE mapping | 28-40K |
| **ExploitSuggester** | Claude Opus 4.5 / MiMo V2.5-Pro | Exploit strategies, payload templates | 26-36K |
| **ReportGenerator** | Claude Haiku 4.5 / MiMo V2.5 | Report synthesis, YARA/Snort rules | 32-48K |
| **ConfigExtractor** | Claude Haiku 4.5 / MiMo V2.5 | Embedded config & credential extraction | 18-24K |
| **Monitor** | Claude Haiku 4.5 / MiMo V2.5 | Health, anomaly detection, ETA estimation | 8-12K |
| **NetworkAnalyzer** | Claude Sonnet 4.5 / MiMo V2.5 | C2 extraction, DGA detection, protocol ID | 22-32K |
| **MemoryForensics** | Claude Sonnet 4.5 / MiMo V2.5 | Process injection, memory artifacts | 24-36K |
| **ThreatIntel** | Claude Opus 4.5 / MiMo V2.5-Pro | MITRE ATT&CK, malware fingerprinting | 28-40K |

## 🔌 LLM Provider Layer

CortexFlow speaks all major LLM dialects through a unified provider abstraction:

| Provider | Models | Pricing (input/output per 1M) |
|---|---|---|
| **Anthropic** | claude-opus-4.5, claude-sonnet-4.5, claude-haiku-4.5 | $3 / $15 |
| **OpenAI** | gpt-4o, gpt-4-turbo, o1, o1-mini | $5 / $15 |
| **Google** | gemini-2.5-pro, gemini-2.5-flash | $1.25 / $5 |
| **Xiaomi MiMo** ⭐ | mimo-v2.5-pro (reasoning), mimo-v2.5 (1M ctx), mimo-v2-omni, TTS variants | $0.14 / $0.56 |
| **Ollama** (local) | llama3.3:70b, deepseek-r1:32b, qwen2.5-coder | **Free** |

Switch providers per-pipeline, per-agent, or globally:

```yaml
# config.yaml
default_provider: mimo
agents:
  exploit_suggester:
    provider: anthropic  # Override per agent
    model: claude-opus-4.5
```

## ✨ Features

### Core Platform
- **10 specialized agents** in a directed acyclic graph (DAG) execution engine
- **5 LLM providers** with unified abstraction and automatic cost tracking
- **YAML workflow templates** for repeatable analysis pipelines
- **JWT + API key authentication** with role-based access control (admin/analyst/viewer)
- **SQLAlchemy persistence** for sessions, runs, token usage, and audit logs
- **Plugin system** with manifest.yaml-based dynamic loading
- **CLI interface** (typer + rich) for shell-driven workflows
- **REST API** (FastAPI) + **WebSocket streaming** + **MCP server** for IDE integration

### Workflow YAML
4 production templates included:
1. **binary_analysis** — full RE pipeline (8 stages, 800K token budget)
2. **code_review** — security-focused code audit with parallel scanning
3. **network_recon** — network IOC extraction and protocol analysis
4. **threat_hunting** — comprehensive 10-agent deep dive (1.5M token budget)

```yaml
# Example: workflows/code_review.yaml (excerpt)
name: code_review
stages:
  - name: code_analyzer
    agent: CodeAnalyzerAgent
    parallel: true
  - name: vuln_scanner
    agent: VulnScannerAgent
    depends_on: [code_analyzer]
```

### Storage & Compliance
- **Audit log** captures every action (login, key creation, pipeline run)
- **Token usage tracking** with per-provider, per-agent aggregation
- **API key lifecycle** (create, rotate, revoke, expiry)
- **Session retention** policies and automatic cleanup

### Plugin System
Drop a `plugins/my_plugin/` directory with `manifest.yaml` + `plugin.py` and CortexFlow auto-discovers and loads it. Plugins can register new agents, providers, or workflow stages.

```python
# plugins/my_plugin/plugin.py
from core.plugin_manager import Plugin
from agents.base_agent import BaseAgent

class MyCustomAgent(BaseAgent):
    async def run(self, context, results):
        # Your logic here
        ...

class MyPlugin(Plugin):
    name = "my_plugin"
    def get_agents(self):
        return {"my_custom": MyCustomAgent}
```

---

## 🚀 Installation

```bash
# Clone
git clone https://github.com/s7537700-sketch/cortexflow.git
cd cortexflow

# Install
pip install -r requirements.txt

# Configure providers (copy and edit .env)
cp .env.example .env

# Initialize database
python -c "from storage import init_db; init_db()"

# Run!
cortexflow serve
```

### Docker (recommended)

```bash
docker compose up
# API:  http://localhost:8000
# Web:  http://localhost:3000
# MCP:  localhost:9000
```

---

## 🔧 Usage

### CLI

```bash
# Show available agents
cortexflow agents list

# List workflow templates
cortexflow workflow list

# Run a workflow
cortexflow workflow run code_review --input ./src

# Direct analysis
cortexflow analyze --target sample.exe --pipeline binary_analysis

# Token statistics
cortexflow tokens stats --since 30d

# Start API server
cortexflow serve --port 8000
```

### REST API

```bash
# Submit analysis
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Authorization: Bearer cf_xxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "codebase",
    "target": "myproject",
    "content": "...",
    "pipeline": "code_review"
  }'

# Check status
curl http://localhost:8000/api/v1/jobs/<job_id>

# Token analytics
curl http://localhost:8000/api/v1/tokens
```

### MCP Integration (Claude Code, OpenCode, Cursor)

```json
// .mcp.json
{
  "mcpServers": {
    "cortexflow": {
      "command": "python",
      "args": ["mcp/server.py"]
    }
  }
}
```

Available MCP tools:
- `cortexflow_analyze` — submit pipeline job
- `cortexflow_scan_code` — quick vulnerability scan
- `cortexflow_get_agents` — list agents
- `cortexflow_get_report` — fetch results

---

## 📊 Token Consumption (with MiMo)

CortexFlow with **Xiaomi MiMo V2.5** (the cheapest production-grade option):

| Pipeline | Tokens | Cost (MiMo) | Cost (Claude Sonnet) |
|---|---|---|---|
| Quick code scan | ~80K | **$0.04** | $0.96 |
| Standard analysis | ~150K | **$0.07** | $1.80 |
| Deep binary analysis | ~300K | **$0.13** | $3.60 |
| Full threat hunt | ~800K | **$0.34** | $9.60 |
| 100 jobs/month | ~15M | **$2** | $54 |

**MiMo is 25x cheaper** — and supports a 1M context window.

---

## 📁 Project Structure

```
cortexflow/
├── agents/                  # 10 specialized agents
│   ├── base_agent.py
│   ├── orchestrator.py
│   ├── code_analyzer.py
│   ├── vuln_scanner.py
│   ├── exploit_suggester.py
│   ├── report_generator.py
│   ├── config_extractor.py        # NEW v2.0
│   ├── monitor_agent.py            # NEW v2.0
│   ├── network_analyzer.py         # NEW v2.0
│   ├── memory_forensics.py         # NEW v2.0
│   └── threat_intel.py             # NEW v2.0
├── providers/               # NEW v2.0 - LLM provider abstraction
│   ├── base.py
│   ├── factory.py
│   ├── anthropic.py
│   ├── openai.py
│   ├── google.py
│   ├── mimo.py                     # Xiaomi MiMo
│   └── ollama.py
├── core/
│   ├── engine.py
│   ├── pipeline.py
│   ├── queue.py
│   ├── token_tracker.py
│   └── plugin_manager.py           # NEW v2.0
├── storage/                 # NEW v2.0 - SQLAlchemy persistence
│   ├── database.py
│   ├── models.py
│   └── repositories.py
├── api/
│   ├── server.py
│   └── auth.py                     # NEW v2.0 - JWT + RBAC
├── cli/                     # NEW v2.0 - Typer CLI
│   └── main.py
├── workflows/               # NEW v2.0 - YAML workflow templates
│   ├── binary_analysis.yaml
│   ├── code_review.yaml
│   ├── network_recon.yaml
│   └── threat_hunting.yaml
├── plugins/                 # NEW v2.0 - Dynamic plugin system
│   └── example_plugin/
│       ├── manifest.yaml
│       └── plugin.py
├── mcp/
│   └── server.py
├── web/
│   ├── index.html
│   ├── css/
│   └── js/
├── tests/                   # NEW v2.0 - pytest suite
│   ├── conftest.py
│   ├── test_agents.py
│   ├── test_providers.py
│   ├── test_storage.py
│   └── test_plugins_auth.py
├── examples/
│   ├── code_review_example.py      # NEW v2.0
│   ├── binary_analysis_example.py  # NEW v2.0
│   └── api_client_example.py       # NEW v2.0
├── docs/
│   └── architecture.md
├── .github/workflows/       # NEW v2.0 - CI/CD
│   ├── ci.yml
│   └── docker-publish.yml
├── pyproject.toml           # NEW v2.0
├── pytest.ini               # NEW v2.0
├── .env.example             # NEW v2.0
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
├── requirements-dev.txt     # NEW v2.0
└── README.md
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# With coverage
pytest tests/ --cov=agents --cov=providers --cov=storage

# Specific test file
pytest tests/test_providers.py -v
```

---

## 🎯 Comparison with Existing Tools

| Feature | CortexFlow v2.0 | Single-agent CLI | LangChain | AutoGPT |
|---|---|---|---|---|
| Specialized security agents | ✅ 10 | ❌ | Generic | Generic |
| Multi-LLM providers | ✅ 5 | Single | Many | Few |
| Workflow YAML | ✅ | ❌ | ❌ | ❌ |
| MITRE ATT&CK mapping | ✅ | ❌ | ❌ | ❌ |
| YARA rule generation | ✅ | ❌ | ❌ | ❌ |
| Memory forensics | ✅ | ❌ | ❌ | ❌ |
| Token tracking + cost | ✅ | ❌ | Partial | ❌ |
| MCP server | ✅ | ❌ | ❌ | ❌ |
| Plugin system | ✅ | ❌ | Partial | ❌ |
| Production-grade | ✅ | Partial | Yes | Demo |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <p><strong>10 agents · 5 LLM providers · YAML workflows · CLI + REST + MCP · Docker · Plugin system</strong></p>
  <p>Built for security researchers, by security researchers.</p>
  <p><sub>v2.0 — Production-grade multi-agent AI orchestration</sub></p>
</div>
