# Invoice Ingestion — Build Guide

## Project Overview
Distributed energy invoice extraction system. Processes PDFs through a multi-pass LLM pipeline, stores results in PostgreSQL, and provides a Next.js review UI.

## Architecture
```
PDF → Blob Storage (imported/) → Azure Function (blob trigger)
  → Pipeline Worker → Pass 0→0.5→1A→1B→2→3→4 → Confidence Gate
  → PostgreSQL + Blob Storage (extracted/) → Human Review UI (Next.js)
```

## Project Structure
- `src/invoice_ingestion/` — Python backend package
- `frontend/` — Next.js human review UI
- `function_app/` — Azure Function (blob trigger)
- `infra/` — Terraform modules for Azure infrastructure
- `tests/` — pytest unit + integration tests
- `docs/` — Specification documents

## Running Locally

### Backend
```bash
# Install dependencies
pip install -e ".[dev]"

# Start PostgreSQL
docker-compose up db -d

# Run database migrations
alembic -c src/invoice_ingestion/storage/migrations/alembic.ini upgrade head

# Start API server
uvicorn invoice_ingestion.api.app:create_app --factory --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

### Full Stack (Docker)
```bash
docker-compose up
```

## Testing
```bash
# Unit tests (no external dependencies needed)
pytest tests/unit/ -v

# Integration tests (requires PostgreSQL)
docker-compose up db -d
pytest tests/integration/ -v -m integration

# Coverage
pytest tests/unit/ --cov=invoice_ingestion --cov-report=html
```

## Key Specs
- `docs/energy-invoice-extraction-algorithm.md` — Core algorithm v2
- `docs/energy-invoice-extraction-international-addendum.md` — International addendum v3

## LLM Configuration (all Azure-deployed)
- **Classification (Pass 0.5):** Claude Haiku via Azure AI Foundry
- **Extraction (Pass 1A/1B):** Claude Sonnet via Azure AI Foundry (vision)
- **Schema Mapping (Pass 2):** Claude Haiku via Azure AI Foundry (text-only)
- **Audit (Pass 4):** GPT-4o via Azure OpenAI (always different provider from extraction)
- **Failover:** Azure AI (Claude) primary → Azure OpenAI (GPT-4o) fallback

## Environment Variables
See `.env.example` for all required configuration. All env vars use `INVOICE_` prefix.
