#!/usr/bin/env bash
# =============================================================================
# GuardRAG — One-Command Setup Script
#
# Usage:
#   ./setup.sh              Interactive setup
#   ./setup.sh --quick      Quick mode (non-interactive)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="GuardRAG"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is required but not installed."
        return 1
    fi
    log_success "$1 is installed"
}

# ---------------------------------------------------------------------------
# Welcome
# ---------------------------------------------------------------------------

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║   🛡️  GuardRAG — Secure Document Q&A with RAG + LLM       ║"
echo "║        Guardrails                                            ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ---------------------------------------------------------------------------
# Prerequisites Check
# ---------------------------------------------------------------------------

log_info "Checking prerequisites..."

MISSING_DEPS=0
check_command "docker" || MISSING_DEPS=1
check_command "docker compose" || MISSING_DEPS=1

if [ $MISSING_DEPS -eq 1 ]; then
    log_error "Please install Docker and Docker Compose first:"
    echo "  https://docs.docker.com/get-docker/"
    exit 1
fi

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

log_info "Setting up configuration..."

ENV_FILE="$SCRIPT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    cp "$SCRIPT_DIR/.env.template" "$ENV_FILE"
    log_success "Created .env from template"
else
    log_warn ".env already exists, keeping existing configuration"
fi

# Check if OpenAI API key is set
if ! grep -q "sk-your-openai-api-key" "$ENV_FILE" 2>/dev/null; then
    log_success "OpenAI API key appears to be configured"
else
    log_warn "OpenAI API key not configured"
    echo ""
    echo "⚠️  GuardRAG requires an OpenAI API key to function."
    echo "   Get one at: https://platform.openai.com/api-keys"
    echo ""

    if [ "${1:-}" != "--quick" ]; then
        read -rp "   Enter your OpenAI API key (or press Enter to skip): " OPENAI_KEY
        if [ -n "$OPENAI_KEY" ]; then
            sed -i.bak "s/sk-your-openai-api-key-here/$OPENAI_KEY/" "$ENV_FILE"
            rm -f "$ENV_FILE.bak"
            log_success "OpenAI API key configured"
        else
            log_warn "No API key provided. You'll need to edit .env manually before starting."
        fi
    else
        log_warn "Quick mode: skipping API key prompt. Edit .env manually."
    fi
fi

# ---------------------------------------------------------------------------
# Build Docker Images
# ---------------------------------------------------------------------------

log_info "Building Docker images..."
cd "$SCRIPT_DIR"
docker compose build --no-cache

log_success "Docker images built successfully"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
log_success "GuardRAG setup complete! 🎉"
echo ""
echo "Next steps:"
echo ""
echo "  1. Start the services:"
echo -e "     ${GREEN}make up${NC}"
echo ""
echo "  2. Or start in foreground to see logs:"
echo -e "     ${GREEN}docker compose up${NC}"
echo ""
echo "  3. Open the web UI:"
echo -e "     ${BLUE}http://localhost${NC}"
echo ""
echo "  4. API documentation:"
echo -e "     ${BLUE}http://localhost/docs${NC} (Swagger UI)"
echo -e "     ${BLUE}http://localhost/redoc${NC} (ReDoc)"
echo ""
echo "  5. Check system health:"
echo -e "     ${GREEN}make health${NC}"
echo ""
echo "Common commands:"
echo -e "  ${GREEN}make help${NC}       Show all available commands"
echo -e "  ${GREEN}make logs${NC}       View service logs"
echo -e "  ${GREEN}make test${NC}       Run the test suite"
echo -e "  ${GREEN}make down${NC}       Stop all services"
echo -e "  ${GREEN}make clean${NC}      Clean build artifacts"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
