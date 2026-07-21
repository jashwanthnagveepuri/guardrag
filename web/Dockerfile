# =============================================================================
# GuardRAG Web — Multi-Stage Dockerfile
# Node 22 → Build React App → Nginx Serve
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — Install dependencies and build the React app
# ---------------------------------------------------------------------------
FROM node:22-alpine AS builder

WORKDIR /build

# Copy package files first for better layer caching
COPY package*.json ./
COPY tsconfig*.json ./
COPY vite.config.ts ./
COPY postcss.config.js ./
COPY tailwind.config.js ./

# Install dependencies
RUN npm ci --prefer-offline --no-audit --no-fund

# Copy source and build
COPY index.html ./
COPY src/ ./src/

# Build for production
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Production — Serve with nginx
# ---------------------------------------------------------------------------
FROM nginx:alpine AS production

LABEL maintainer="Jashwanth Nag Veepuri"
LABEL description="GuardRAG Web UI — React 18 + TypeScript"
LABEL version="1.0.0"

# Copy built assets from builder
COPY --from=builder /build/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create required nginx directories and set permissions
RUN mkdir -p /var/cache/nginx/client_temp /var/run/nginx \
    && chown -R nginx:nginx /var/cache/nginx /var/run/nginx /usr/share/nginx/html

# Use non-root nginx user
USER nginx

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
