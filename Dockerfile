# =============================================================================
# GuardRAG API — Multi-Stage Dockerfile
# Python 3.13 → Dependencies → Source → Production
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — Install build dependencies and Python packages
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

WORKDIR /build

# Install build tools and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry for dependency management
RUN pip install --no-cache-dir poetry==1.8.0

# Copy dependency files
COPY pyproject.toml poetry.lock* ./
COPY guardrag/__init__.py guardrag/__init__.py

# Install dependencies without virtualenv (production mode)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --without dev --no-root

# ---------------------------------------------------------------------------
# Stage 2: Production — Minimal runtime image
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS production

LABEL maintainer="Jashwanth Nag Veepuri"
LABEL description="GuardRAG — Secure Document Q&A with RAG + LLM Guardrails"
LABEL version="1.0.0"

WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1000 guardrag \
    && useradd --uid 1000 --gid guardrag --shell /bin/false --create-home guardrag

# Install runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY guardrag/ ./guardrag/
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Create upload directory
RUN mkdir -p /app/uploads && chown -R guardrag:guardrag /app

# Switch to non-root user
USER guardrag

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "guardrag.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

# ---------------------------------------------------------------------------
# Stage 3: Development — Includes dev dependencies and hot reload
# ---------------------------------------------------------------------------
FROM builder AS development

WORKDIR /app

# Install dev dependencies
RUN poetry install --no-interaction --no-ansi --no-root

# Copy full source
COPY . .

EXPOSE 8000

CMD ["uvicorn", "guardrag.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
