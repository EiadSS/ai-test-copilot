# AI Test Automation Copilot (Starter)

This is a starter repo for an **AI Test Automation Copilot**:
- Upload PRDs / requirements docs and OpenAPI specs
- Ingest + chunk + embed into **Postgres + pgvector**
- Generate a **test plan** using RAG + OpenAI
- Query document chunks via semantic search

## Local setup

**Prereqs:** Docker Desktop + Docker Compose

1) Copy env:
```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY
```

2) Start services:
```bash
docker compose up --build
```

3) Open API docs:
- http://localhost:8000/docs

## Quick demo (curl)

Create a project:
```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo Project"}'
```

Upload a document (txt/md/openapi yaml/json/pdf):
```bash
curl -X POST "http://localhost:8000/api/projects/<PROJECT_ID>/documents" \
  -F "file=@./some_doc.md"
```

Semantic search:
```bash
curl "http://localhost:8000/api/projects/<PROJECT_ID>/search?q=login%20flow"
```

Generate a test plan (async job):
```bash
curl -X POST "http://localhost:8000/api/projects/<PROJECT_ID>/generate/test-plan"
curl "http://localhost:8000/api/jobs/<JOB_ID>"
curl "http://localhost:8000/api/projects/<PROJECT_ID>/test-plans/latest"
```

