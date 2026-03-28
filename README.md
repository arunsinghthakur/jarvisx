# JarvisX

[![GitHub stars](https://img.shields.io/github/stars/arunsinghthakur/jarvisx?style=flat-square)](https://github.com/arunsinghthakur/jarvisx/stargazers)
[![License: GPL v3](https://img.shields.io/badge/license-GPLv3-blue?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13+-blue?style=flat-square)](https://python.org)
[![Website](https://img.shields.io/badge/docs-website-6366f1?style=flat-square)](https://arunsinghthakur.github.io/jarvisx-docs/)

A multi-tenant AI workflow automation platform. Build intelligent automations with multi-agent orchestration, connect your tools, and interact through voice or text.

**[Website](https://arunsinghthakur.github.io/jarvisx-docs/)** | **[Getting Started](#setup-from-scratch)** | **[API Reference](#api-reference)**

---

## Key Features


| Category                      | Capabilities                                                                                                                                      |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Multi-Agent Orchestration** | 9 system agents (orchestrator, developer, browser, researcher, knowledge, PII guardian, audit, policy, governance) + custom dynamic agents via UI |
| **Visual Workflow Builder**   | 25 node types, drag-and-drop canvas, loops, fork/join, error handling, sub-workflows, undo/redo, copy/paste                                       |
| **Multi-Tenancy**             | Organizations, workspaces, teams with role-based access (Owner, Admin, Member, Viewer)                                                            |
| **Voice & Text Chat**         | WebSocket-based low-latency voice with Silero VAD, rich content rendering (charts, tables, LaTeX, Mermaid)                                        |
| **Knowledge Base**            | RAG with semantic search over documents, snippets, and URLs using pgvector                                                                        |
| **Compliance**                | PII detection/masking, audit logging, policy enforcement, governance reports                                                                      |
| **Observability**             | LangFuse distributed tracing for workflow executions, cost tracking per workflow/agent/model                                                      |
| **Integrations**              | Database, S3, Google Sheets, Slack, Teams, Email, HTTP/REST + MCP tools (Shell, Playwright, Tavily)                                               |


---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                           Apps                                   │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │  Admin UI   │  │ Voice Chat  │                               │
│  │   :5003     │  │   :5001     │                               │
│  └──────┬──────┘  └──────┬──────┘                               │
└─────────┼────────────────┼──────────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Services                                 │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │  Admin API  │  │Voice Gateway│                               │
│  │   :5002     │  │   :9003     │                               │
│  └──────┬──────┘  └──────┬──────┘                               │
│         │                │                                       │
│         │         ┌──────┴──────┐                                │
│         │         │ Orchestrator│ ◄── Runs in-process with       │
│         │         │  (LlmAgent) │    RemoteA2AAgent sub-agents   │
│         │         └──────┬──────┘                                │
│         │                │ A2A Protocol                          │
│         │    ┌───────┬───┴───┬───────┬───────┐                  │
│         │    ▼       ▼       ▼       ▼       ▼                  │
│         │ Developer Browser Researcher Knowledge + 4 Compliance │
│         │  :9000    :9004    :9005    :9006    :9007-9010        │
│         │                                                        │
│         └──────────────┬─────────────────────────────────────────│
│                        ▼                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │PostgreSQL│  │  Redis   │  │ LangFuse │                       │
│  │  :5434   │  │  :6379   │  │  :3100   │                       │
│  └──────────┘  └──────────┘  └──────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

The platform uses Google's Agent Development Kit (ADK) with the A2A (Agent-to-Agent) protocol. All agents are built as `LlmAgent` instances and exposed via `to_a2a()`. The orchestrator connects to sub-agents using `RemoteA2AAgent`. Dynamic agents (created via UI) run in-process with the orchestrator.

---

## Setup from Scratch

Complete guide to get JarvisX running on a fresh machine.

### Step 1: Prerequisites


| Requirement             | Version | Check                                                                       |
| ----------------------- | ------- | --------------------------------------------------------------------------- |
| Python                  | 3.13+   | `python3 --version`                                                         |
| uv (package manager)    | Latest  | `uv --version` (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`) |
| Node.js                 | 18+     | `node --version`                                                            |
| npm                     | 9+      | `npm --version`                                                             |
| Docker & Docker Compose | Latest  | `docker --version`                                                          |
| Git                     | Any     | `git --version`                                                             |


### Step 2: Clone and Create Virtual Environment

```bash
git clone https://github.com/arunsinghthakur/jarvisx.git
cd jarvisx

# Create virtual environment
uv venv .venv
source .venv/bin/activate

# Install Python dependencies
uv pip install -e ./packages/core
uv pip install -e .
```

### Step 3: Create Environment File

Create a `.env` file in the project root. Below is the minimal configuration to get started:

```bash
# ──────────────────────────────────────────────
# Database (auto-started via Docker)
# ──────────────────────────────────────────────
POSTGRES_HOST=localhost
POSTGRES_PORT=5434
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=jarvisx
POSTGRES_SCHEMA=jarvisx

# ──────────────────────────────────────────────
# Service Ports
# ──────────────────────────────────────────────
ADMIN_API_PORT=5002
ADMIN_UI_PORT=5003
UI_REACT_VOICE_CHAT_PORT=5001
VOICE_GATEWAY_PORT=9003

# ──────────────────────────────────────────────
# Security (CHANGE THESE IN PRODUCTION)
# ──────────────────────────────────────────────
LLM_ENCRYPTION_KEY=your-secret-key-change-in-production
SSO_ENCRYPTION_KEY=your-sso-key-change-in-production

# ──────────────────────────────────────────────
# LangFuse Observability (optional)
# ──────────────────────────────────────────────
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://localhost:3100
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=

# ──────────────────────────────────────────────
# Redis (for SSO session storage, optional)
# ──────────────────────────────────────────────
REDIS_HOST=localhost
REDIS_PORT=6379

# ──────────────────────────────────────────────
# Search API (for Researcher agent, optional)
# ──────────────────────────────────────────────
TAVILY_API_KEY=

# ──────────────────────────────────────────────
# SMTP (for email verification, optional)
# ──────────────────────────────────────────────
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=
```

### Step 4: Start Infrastructure

```bash
# Start PostgreSQL and Redis via Docker
cd infra/docker
docker compose -f docker-compose.dev.yml up -d
cd ../..

# Optional: Start LangFuse for observability
cd infra/docker
docker compose up -d langfuse-postgres langfuse-clickhouse langfuse-redis langfuse-minio langfuse
cd ../..
```

### Step 5: Run Database Migrations

```bash
uv run alembic -c migrations/alembic.ini upgrade head
```

### Step 6: Install Frontend Dependencies

```bash
# Admin UI
cd apps/admin && npm install && cd ../..

# Voice Chat
cd apps/chat && npm install && cd ../..
```

### Step 7: Start the Platform

**Option A: All-in-one script**

```bash
python3 -m scripts.start_all
```

This starts: PostgreSQL, Redis, LangFuse (if enabled), runs migrations, Admin API (:5002), Voice Gateway (:9003), Admin UI (:5003), and Voice Chat (:5001).

**Option B: Start services individually**

```bash
# Terminal 1: Admin API
uv run python3 -m services.api.admin.src

# Terminal 2: Voice Gateway
uv run python3 -m services.gateways.voice.src

# Terminal 3: Admin UI
cd apps/admin && npm start

# Terminal 4: Voice Chat
cd apps/chat && npm start
```

### Step 8: Access the Platform


| Service               | URL                                                      |
| --------------------- | -------------------------------------------------------- |
| Admin UI              | [http://localhost:5003](http://localhost:5003)           |
| Voice Chat            | [http://localhost:5001](http://localhost:5001)           |
| Admin API (Swagger)   | [http://localhost:5002/docs](http://localhost:5002/docs) |
| LangFuse (if enabled) | [http://localhost:3100](http://localhost:3100)           |


### Step 9: First-Time Configuration

1. **Sign up** at [http://localhost:5003](http://localhost:5003) -- the first organization created becomes the platform admin
2. **Configure LLM** -- Go to Settings > LLM Settings > Add LLM Config. Choose your provider (OpenAI, Anthropic, Azure, Google Vertex, or LiteLLM Proxy) and enter API credentials
3. **Create a workspace** -- Go to Workspaces > Create Workspace
4. **Test it** -- Open Voice Chat at [http://localhost:5001/workspace/{workspace-id}](http://localhost:5001/workspace/{workspace-id}) and start chatting

---

## Quick Start (Existing Setup)

If you already have dependencies installed:

```bash
cd jarvisx
source .venv/bin/activate
python3 -m scripts.start_all
```

---

## Docker Deployment

For containerized deployment of the core platform services:

```bash
cd infra/docker
docker compose up -d
```

This starts: PostgreSQL, Redis, LangFuse stack, Admin API, Voice Gateway, Admin UI, and Voice Chat.

Note: A2A agent processes (developer, browser, researcher, knowledge, compliance) are not started as separate containers in the default compose file. They run in-process via the orchestrator when invoked.

---

## System Agents


| Agent        | Port       | Description                                                        |
| ------------ | ---------- | ------------------------------------------------------------------ |
| Orchestrator | in-process | Central router that delegates tasks to specialized agents          |
| Developer    | 9000       | Code generation, debugging, and programming assistance             |
| Browser      | 9004       | Web browsing, form filling, and data extraction via Playwright     |
| Researcher   | 9005       | Real-time web search and information retrieval via Tavily          |
| Knowledge    | 9006       | Semantic search over workspace knowledge base (RAG with pgvector)  |
| PII Guardian | 9007       | Detects, classifies, and masks personally identifiable information |
| Audit        | 9008       | Logs and tracks system activities for compliance auditing          |
| Policy       | 9009       | Evaluates requests against organizational policies                 |
| Governance   | 9010       | Enforces data retention and compliance governance                  |


### Dynamic Agents

Create custom agents directly from the Admin UI without writing code:

1. Go to Settings > LLM Settings > ensure an LLM config exists
2. Go to Agents > Add Agent > select "Dynamic Agent"
3. Configure name, system prompt, select LLM config, and assign MCP tools
4. Save -- the agent is immediately available to the orchestrator

Dynamic agents are organization-scoped and run in-process (no separate service needed).

---

## Workflow Automation

A visual workflow builder similar to n8n/Zapier with 25 node types:

### Node Types


| Category         | Nodes                                                                                  |
| ---------------- | -------------------------------------------------------------------------------------- |
| **Triggers**     | Manual, Schedule (cron), Webhook, Chatbot, Agent Event                                 |
| **Actions**      | Agent, HTTP Request, Transform, Sub-Workflow                                           |
| **Logic**        | Condition, Loop, Switch, For Each                                                      |
| **Flow Control** | Fork, Join, Delay, Error Handler, Approval                                             |
| **Integrations** | Database (SQL), Cloud Storage (S3), Google Sheets, Data Transform, Python Code         |
| **I/O**          | Read File, Save File, Send Email, Notification (Slack/Teams/Discord), Webhook Response |
| **Annotations**  | Comment, Group                                                                         |


### Canvas Features

- **Undo/Redo** (Ctrl+Z / Ctrl+Shift+Z)
- **Copy/Paste** nodes and edges (Ctrl+C / Ctrl+V)
- **Comments** -- sticky note annotations
- **Groups** -- visual node grouping
- **Live Execution** -- real-time node status overlay during workflow runs
- **Retry Policies** -- per-node configurable retry with exponential backoff
- **Dead Letter Queue** -- failed nodes queued for manual review
- **Versioning** -- automatic snapshots on save, rollback to any version
- **Debugging** -- step-through execution with data inspection and breakpoints
- **Templates** -- pre-built workflow templates, export/import as JSON
- **Cost Tracking** -- LLM token usage and cost estimates per workflow

### Variable Interpolation

Reference data from previous nodes using `{{input.field}}`:

```
Agent prompt:   "Search for {{input.query}}"
HTTP body:      {"user": "{{input.userId}}"}
Condition:      input.status === 'success'
```

---

## Multi-Tenancy


| Concept           | Description                                                                                         |
| ----------------- | --------------------------------------------------------------------------------------------------- |
| **Organizations** | Top-level entities representing companies/customers                                                 |
| **Workspaces**    | Isolated environments within an org (dev, staging, prod)                                            |
| **Teams**         | Groups of users with roles (Owner, Admin, Member, Viewer), optionally scoped to specific workspaces |
| **Users**         | Individual accounts with email verification                                                         |


### Platform Admin vs Tenant Admin


| Capability         | Platform Admin          | Tenant Admin        |
| ------------------ | ----------------------- | ------------------- |
| System Agents/MCPs | Full CRUD               | Read-only           |
| Custom Agents/MCPs | Full CRUD               | Full CRUD (own org) |
| LLM Config         | Own org + .env fallback | Own org (required)  |
| Platform Dashboard | Full access             | No access           |
| Platform Settings  | Full access             | No access           |


---

## Compliance & Governance

Built-in compliance agents for enterprise security:

- **PII Detection** -- automatically detect and mask PII (email, phone, SSN, credit cards, etc.)
- **Audit Logging** -- comprehensive audit trail with PII masking
- **Policy Enforcement** -- configurable rules for data protection, access control, content filtering
- **Governance Reports** -- SOC2, GDPR, HIPAA compliance assessments

Managed at the organization level in Admin UI > Compliance.

---

## Knowledge Base

Build and manage knowledge bases per organization:

- **Document upload** -- PDF, Word, text files with automatic chunking
- **Snippets** -- manual text entries
- **URL indexing** -- crawl and index web pages
- **Semantic search** -- pgvector embeddings with cosine similarity
- **RAG integration** -- Knowledge agent automatically searches relevant context

---

## Configuration

Configuration is organized into three tiers:


| Tier               | Source                       | Changeable at Runtime | Examples                                       |
| ------------------ | ---------------------------- | --------------------- | ---------------------------------------------- |
| **Infrastructure** | `.env` file                  | No (restart required) | DB host, ports, API keys, encryption keys      |
| **Operational**    | Database (Platform Settings) | Yes (via admin UI)    | Tracing sample rate, cache TTLs, feature flags |
| **Tenant**         | Database (per-org)           | Yes (via admin UI)    | LLM configs, SSO, integrations                 |


Infrastructure settings are grouped into frozen dataclasses in `packages/core/jarvisx/config/configs.py`. All variables are accessed as module-level constants (e.g., `from jarvisx.config.configs import POSTGRES_HOST`). Do not use `os.getenv()` directly in other files.

Operational settings are managed via `PlatformSettingsService.get(category, key, default)` with 60-second caching and `.env` fallback.

### Key Environment Variables


| Variable                   | Description                              | Default     |
| -------------------------- | ---------------------------------------- | ----------- |
| `POSTGRES_HOST`            | Database host                            | `localhost` |
| `POSTGRES_PORT`            | Database port                            | `5434`      |
| `POSTGRES_DB`              | Database name                            | `jarvisx`   |
| `LLM_ENCRYPTION_KEY`       | Key for encrypting stored API keys       | (required)  |
| `SSO_ENCRYPTION_KEY`       | Key for SSO secrets                      | (required)  |
| `LANGFUSE_ENABLED`         | Enable distributed tracing               | `true`      |
| `LANGFUSE_TRACE_WORKFLOWS` | Trace workflow executions                | `true`      |
| `LANGFUSE_TRACE_LLM`       | Trace LLM calls (off by default)         | `false`     |
| `LANGFUSE_TRACE_API`       | Trace API requests (off by default)      | `false`     |
| `LANGFUSE_SAMPLE_RATE`     | Sampling rate for traced decorator spans | `0.1`       |
| `TAVILY_API_KEY`           | Tavily API key for Researcher agent      | (optional)  |
| `SMTP_HOST`                | SMTP server for email verification       | (optional)  |
| `REDIS_HOST`               | Redis host for SSO sessions              | `localhost` |


See `packages/core/jarvisx/config/configs.py` for the complete list of all variables and their defaults.

---

## Observability (LangFuse)

Integrated distributed tracing via LangFuse. By default, only **workflow execution traces** are captured. LLM and API tracing are off to minimize storage.

### Setup

1. Start LangFuse: `cd infra/docker && docker compose up -d langfuse langfuse-postgres langfuse-clickhouse langfuse-redis`
2. Open [http://localhost:3100](http://localhost:3100), sign up, go to Settings > API Keys, create a key pair
3. Add to `.env`: `LANGFUSE_PUBLIC_KEY=pk-lf-...` and `LANGFUSE_SECRET_KEY=sk-lf-...`

### Enable/Disable Tracing

Set in `.env` or toggle at runtime via Admin UI > Platform Settings:

```bash
LANGFUSE_TRACE_WORKFLOWS=true    # ON  -- always trace workflow executions
LANGFUSE_TRACE_LLM=false         # OFF -- set true to trace LLM calls (for debugging)
LANGFUSE_TRACE_API=false          # OFF -- set true to trace API requests
LANGFUSE_SAMPLE_RATE=0.1          # 10% sampling for @traced decorator spans
LANGFUSE_LLM_INPUT_LIMIT=500     # Truncate logged LLM inputs to 500 chars
LANGFUSE_LLM_OUTPUT_LIMIT=500    # Truncate logged LLM outputs to 500 chars
```

---

## Voice Architecture

WebSocket-based bidirectional streaming for low-latency voice conversations:

- **Endpoint**: `ws://localhost:9003/ws/voice`
- **Voice Activity Detection**: Silero VAD (~300ms speech end detection)
- **Streaming audio**: PCM16 chunks streamed in real-time
- **Phrase-level TTS**: Server chunks responses at phrase boundaries, generates TTS in parallel
- **Pre-buffered playback**: Audio plays immediately as chunks arrive

**Latency**: 300-800ms end-to-end.

Legacy HTTP endpoints remain available for backward compatibility: `POST /api/audio/transcribe-only`, `POST /api/audio/tts`, `POST /api/chat`.

---

## API Reference

### Authentication


| Method | Endpoint                    | Description     |
| ------ | --------------------------- | --------------- |
| POST   | `/api/auth/login`           | Login           |
| POST   | `/api/auth/logout`          | Logout          |
| GET    | `/api/auth/me`              | Current user    |
| POST   | `/api/auth/change-password` | Change password |


### Organizations & Workspaces


| Method         | Endpoint                     | Description                       |
| -------------- | ---------------------------- | --------------------------------- |
| GET/POST       | `/api/organizations`         | List / Create organizations       |
| GET/PUT/DELETE | `/api/organizations/{id}`    | Get / Update / Delete             |
| GET/POST       | `/api/workspaces`            | List / Create workspaces          |
| GET            | `/api/workspace-config/{id}` | Get workspace config for chat app |


### Agents & MCPs


| Method     | Endpoint                     | Description               |
| ---------- | ---------------------------- | ------------------------- |
| GET/POST   | `/api/available/agents`      | List / Create agents      |
| PUT/DELETE | `/api/available/agents/{id}` | Update / Delete agent     |
| GET/POST   | `/api/mcps`                  | List / Create MCP servers |


### Workflows


| Method         | Endpoint                                     | Description             |
| -------------- | -------------------------------------------- | ----------------------- |
| GET/POST       | `/api/workflows`                             | List / Create workflows |
| GET/PUT/DELETE | `/api/workflows/{id}`                        | Get / Update / Delete   |
| POST           | `/api/workflows/{id}/execute`                | Execute workflow        |
| GET            | `/api/workflows/{id}/executions`             | Execution history       |
| GET            | `/api/workflows/{id}/versions`               | Version history         |
| POST           | `/api/workflows/{id}/versions/{vid}/restore` | Rollback                |
| POST           | `/api/workflows/{id}/debug/start`            | Start debug session     |
| GET            | `/api/workflows/{id}/export`                 | Export as JSON          |
| POST           | `/api/webhooks/{workflow_id}`                | Webhook trigger         |


### Templates


| Method | Endpoint                           | Description      |
| ------ | ---------------------------------- | ---------------- |
| GET    | `/api/workflow-templates`          | Browse templates |
| POST   | `/api/workflow-templates/{id}/use` | Clone template   |
| POST   | `/api/workflow-templates`          | Save as template |


### Dashboard & Costs


| Method | Endpoint                           | Description                   |
| ------ | ---------------------------------- | ----------------------------- |
| GET    | `/api/dashboard/stats`             | Dashboard statistics          |
| GET    | `/api/dashboard/costs`             | Cost summary (today, 7d, 30d) |
| GET    | `/api/dashboard/costs/by-workflow` | Cost by workflow              |
| GET    | `/api/dashboard/costs/by-agent`    | Cost by model                 |
| GET    | `/api/dashboard/costs/trends`      | Daily cost trends             |


### Chatbot


| Method | Endpoint                                   | Description                  |
| ------ | ------------------------------------------ | ---------------------------- |
| POST   | `/api/chatbot/{workflow_id}/chat`          | Send message (SSE streaming) |
| GET    | `/api/chatbot/{workflow_id}/conversations` | List conversations           |


### Platform (Admin only)


| Method  | Endpoint                 | Description      |
| ------- | ------------------------ | ---------------- |
| GET     | `/api/platform/overview` | Platform metrics |
| GET/PUT | `/api/platform/settings` | Runtime settings |


---

## Development Guide

### Adding a Dynamic Agent (Recommended)

No code needed. Use Admin UI > Agents > Add Agent > Dynamic Agent. Configure name, prompt, LLM config, and MCP tools.

### Adding a System Agent (Code-Based)

For agents requiring custom logic:

```bash
# 1. Create agent directory
mkdir -p services/agents/my_agent/src

# 2. Create agent.py
cat > services/agents/my_agent/src/agent.py << 'EOF'
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

def create_my_agent(mcp_tools: list = None) -> LlmAgent:
    return LlmAgent(
        name="my_agent",
        model=LiteLlm(model="vertex_ai/gemini-2.5-flash"),
        description="Description for the orchestrator",
        instruction="System prompt for the agent",
        tools=mcp_tools or [],
    )
EOF

# 3. Register in packages/core/jarvisx/config/constants.py (SystemAgentCodes)
# 4. Create a DB migration to seed the agent record
# 5. Optionally create a Dockerfile in infra/docker/services/
```

### Adding a Workflow Node Type

```bash
# 1. Create executor in packages/core/jarvisx/workflows/nodes/my_node.py
# 2. Register in packages/core/jarvisx/workflows/nodes/__init__.py
# 3. Create frontend component in apps/admin/src/components/workflows/nodes/MyNode.jsx
# 4. Register in WorkflowEditor.jsx (nodeTypes, palette, config form, minimap color)
```

### Project Structure

```
jarvisx/
├── apps/
│   ├── admin/                  # Admin dashboard (React)
│   └── chat/                   # Voice/text chat interface (React)
├── packages/
│   ├── core/                   # Shared Python library (jarvisx)
│   │   └── jarvisx/
│   │       ├── a2a/            # Agent-to-Agent utilities
│   │       ├── config/         # Configuration (dataclass groups)
│   │       ├── database/       # SQLAlchemy models and session
│   │       ├── mcp/            # MCP server configs and loaders
│   │       ├── services/       # Shared services (email, settings)
│   │       ├── tracing/        # LangFuse integration, cost tracking
│   │       └── workflows/      # Workflow engine and 25 node executors
│   └── ui-shared/              # Shared frontend components
├── services/
│   ├── agents/                 # AI agents (9 total)
│   │   ├── orchestrator/       # Central routing agent
│   │   ├── developer/          # Code assistance
│   │   ├── browser/            # Web automation
│   │   ├── researcher/         # Web search
│   │   ├── knowledge/          # RAG knowledge base
│   │   ├── pii_guardian/       # PII detection
│   │   ├── audit/              # Audit logging
│   │   ├── policy/             # Policy enforcement
│   │   └── governance/         # Compliance governance
│   ├── api/admin/              # Admin API (FastAPI, 24 routers)
│   └── gateways/voice/         # Voice gateway (WebSocket + HTTP)
├── infra/docker/               # Docker Compose, Dockerfiles
├── migrations/                 # Alembic database migrations
└── scripts/                    # Utility scripts (start_all.py)
```

---

## Troubleshooting


| Issue                          | Solution                                                                 |
| ------------------------------ | ------------------------------------------------------------------------ |
| `ModuleNotFoundError: jarvisx` | Run `uv pip install -e ./packages/core && uv pip install -e .`           |
| `alembic: command not found`   | Use `uv run alembic` or `.venv/bin/python -m alembic`                    |
| Port already in use            | `lsof -i :PORT` to find the process, `kill PID` to stop it               |
| Docker containers not starting | `docker compose down && docker compose up -d`                            |
| LLM config error in chat       | Go to Admin UI > Settings > LLM Settings and add a config                |
| Voice not working              | Ensure Voice Gateway is running on :9003 and mic permissions are granted |
| Database migration fails       | Check PostgreSQL is running: `docker ps | grep postgres`                 |
| Frontend not loading           | Run `npm install` in `apps/admin/` and `apps/chat/`                      |


