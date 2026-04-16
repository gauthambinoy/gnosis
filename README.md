# 🧠 Gnosis — AI Agent Orchestration Platform

> Build, deploy, and manage intelligent AI agents with a powerful orchestration engine.

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![Next.js](https://img.shields.io/badge/next.js-16-black)

## ✨ Features

- **🤖 Agent Management** — Create, configure, and orchestrate AI agents with custom tools and prompts
- **⚡ Multi-LLM Routing** — Intelligent routing across OpenAI, Anthropic, Ollama with 4-tier strategy (cache → fast → standard → deep)
- **🛡️ Guardrails** — Built-in content safety, prompt injection detection, and output validation
- **📊 Real-time Monitoring** — Prometheus metrics, execution tracking, and audit logging
- **🔒 Enterprise Security** — JWT auth, rate limiting, PII scrubbing, CORS hardening
- **📦 Agent Templates** — Pre-built agent archetypes for common use cases
- **🔄 Workflow Orchestration** — DAG-based pipelines, scheduled tasks, and event-driven execution
- **🧠 Knowledge Base** — RAG with FAISS vector search and document ingestion
- **🌐 Multi-workspace** — Team collaboration with role-based access control
- **📱 Modern Dashboard** — Next.js 16 frontend with real-time updates

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend    │────▶│  LLM Router  │
│  Next.js 16  │     │  FastAPI     │     │  4-Tier      │
│  TypeScript  │     │  SQLAlchemy  │     │  Routing     │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                  ┌─────────┼─────────┐
                  │         │         │
            ┌─────▼──┐ ┌───▼───┐ ┌───▼───┐
            │PostgreSQL│ │ Redis │ │ FAISS │
            │  + async │ │ cache │ │vectors│
            └─────────┘ └───────┘ └───────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL (optional — runs in-memory for development)

### Development Setup

```bash
# Clone
git clone https://github.com/gauthambinoy/gnosis.git
cd gnosis

# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # Edit with your settings
python3 -m uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Docker (Recommended)

```bash
docker-compose up -d
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (admin/gnosis)
```

## 📖 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health**: http://localhost:8000/api/v1/health

## 🧪 Testing

```bash
cd backend
python3 -m pytest tests/ -v
```

## 📊 Monitoring

- **Prometheus**: Scrapes `/metrics` endpoint with request rates, latencies, error counts
- **Grafana**: Pre-configured dashboard at port 3001

## 🏛️ Project Structure

```
gnosis/
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/       # Route handlers (40+ endpoints)
│   │   ├── core/      # Business logic engines
│   │   ├── models/    # SQLAlchemy ORM models
│   │   └── schemas/   # Pydantic request/response schemas
│   └── tests/         # pytest test suite
├── frontend/          # Next.js 16 application
│   └── src/
│       ├── app/       # App router pages (32+ routes)
│       ├── components/ # React components
│       └── lib/       # Utilities and API client
├── infra/             # Infrastructure as Code
│   ├── terraform/     # AWS ECS, RDS, S3
│   └── prometheus/    # Monitoring config
├── scripts/           # Utility scripts
└── docker-compose.yml # Full stack orchestration
```

## 📄 License

MIT
