# Multi-stage build for MCP Learning Server
FROM python:3.10-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock* ./
COPY src/ src/
COPY scripts/ scripts/
COPY README.md ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.10-slim as runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    ca-certificates \\
    && rm -rf /var/lib/apt/lists/* \\
    && apt-get clean

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 mcp-user

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/src /app/src
COPY --from=builder /app/scripts /app/scripts
COPY --from=builder /app/README.md /app/

# Copy configuration files
COPY .env.example .env

# Create directories for logs and data
RUN mkdir -p /app/logs /app/data /app/uploads && \\
    chown -R mcp-user:mcp-user /app

# Switch to non-root user
USER mcp-user

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV DEBUG=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "scripts/start_server.py", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]