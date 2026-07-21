### GuardRAG — Secure Document Q&A with RAG + LLM Guardrails

**Personal Project** | July 2025 | Python, FastAPI, LangChain, ChromaDB, React, OpenAI

**What it is:** A production-grade RAG (Retrieval-Augmented Generation) system with a 3-layer LLM guardrail architecture that secures document Q&A against prompt injection, data exfiltration, and hallucination. Unlike typical RAG tutorials that skip security entirely, GuardRAG demonstrates how to build enterprise-safe AI applications with observable, configurable safety controls at every stage.

**Architecture:** End-to-end RAG pipeline with document ingestion (PDF/TXT/MD/DOCX), recursive + semantic chunking, OpenAI text-embedding-3-large vectorization, ChromaDB storage with MMR retrieval, cross-encoder re-ranking (ms-marco-MiniLM), and GPT-4o generation — protected by input validation (200+ regex patterns + LLM classifier), retrieval filtering (PII redaction + toxic content filtering), and output verification (NLI-based hallucination detection with confidence scoring).

**Key technical contributions:**

- **Designed and implemented a 2-stage input guardrail** achieving 96.9% detection rate on known adversarial prompts: Stage 1 uses 200+ compiled regex patterns with DAN framework detection and encoding evasion analysis (<10ms); Stage 2 uses GPT-4o-mini structured JSON classification (~300ms). Escalation logic ensures only 15% of queries incur LLM latency overhead.
- **Built NLI-based hallucination detection** using cross-encoder/nli-deberta-v3-base for per-sentence entailment verification against retrieved source chunks, combined with cross-encoder/ms-marco-MiniLM-L-6-v2 answer relevance scoring and a weighted composite confidence formula (retrieval x 0.3 + faithfulness x 0.4 + relevance x 0.3).
- **Implemented full RAG pipeline** supporting 4 document formats, 2 chunking strategies (recursive + semantic), OpenAI embeddings (3072 dims), ChromaDB MMR retrieval, and cross-encoder re-ranking — all exposed through a type-safe FastAPI backend with OpenAPI documentation.
- **Developed React 18 + TypeScript frontend** with real-time SSE streaming chat, confidence meters, source citation panels, guardrail dashboards, and document management — communicating with the backend through a unified nginx reverse proxy.
- **Created 80+ test cases** using pytest-asyncio with mocked external APIs (OpenAI, ChromaDB), achieving >80% code coverage across API routes (documents, chat, guardrails, system) and core services (parsers, guardrails).
- **Built Docker Compose stack** with PostgreSQL 16, ChromaDB, Redis, FastAPI, and nginx — including health checks, resource limits, and network isolation. CI/CD pipeline with GitHub Actions runs lint (ruff), test (pytest with coverage), type check (mypy), Docker builds, and Trivy security scanning on every push to main.
- **Wrote comprehensive technical README** with Mermaid architecture diagrams, guardrail benchmark tables, API documentation, and development guides — designed to showcase AI/ML engineering depth to senior interviewers.

**Impact:** Demonstrates production-grade AI safety architecture that most RAG implementations ignore. The 3-layer guardrail design (input → retrieval → output) provides defense in depth for enterprise LLM deployments, with each layer independently configurable and fully auditable. This project complements mcp-opsmate in showcasing full-stack AI engineering capabilities from infrastructure automation to secure LLM application development.

**Links:** GitHub: https://github.com/Freakycobra/guardrag
