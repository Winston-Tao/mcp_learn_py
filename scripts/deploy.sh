#!/bin/bash

# MCP Learning Server Deployment Script
# Usage: ./scripts/deploy.sh [environment] [options]

set -euo pipefail

# Default values
ENVIRONMENT="${1:-development}"
BUILD_IMAGE="${BUILD_IMAGE:-true}"
PULL_LATEST="${PULL_LATEST:-false}"
BACKUP_DATA="${BACKUP_DATA:-true}"
RUN_TESTS="${RUN_TESTS:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if script is run from project root
if [[ ! -f "pyproject.toml" ]]; then
    log_error "This script must be run from the project root directory"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    log_error "docker-compose is not installed. Please install it and try again."
    exit 1
fi

log_info "Starting deployment for environment: $ENVIRONMENT"

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    mkdir -p logs data uploads nginx/ssl backups monitoring/grafana monitoring/prometheus
    chmod 755 logs data uploads
}

# Load environment variables
load_environment() {
    if [[ -f ".env" ]]; then
        log_info "Loading environment variables from .env file"
        set -a
        source .env
        set +a
    else
        log_warning ".env file not found. Using default values."
        if [[ ! -f ".env.example" ]]; then
            log_error ".env.example file not found. Cannot proceed without environment configuration."
            exit 1
        fi
        log_info "Copying .env.example to .env"
        cp .env.example .env
        log_warning "Please edit .env file with your configuration before running again."
        exit 1
    fi
}

# Backup existing data
backup_data() {
    if [[ "$BACKUP_DATA" == "true" && -d "data" ]]; then
        log_info "Creating backup of existing data..."
        BACKUP_DIR="backups/backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"

        if [[ -d "data" ]] && [[ "$(ls -A data)" ]]; then
            cp -r data/* "$BACKUP_DIR/" 2>/dev/null || true
        fi

        if [[ -d "logs" ]] && [[ "$(ls -A logs)" ]]; then
            cp -r logs/*.log "$BACKUP_DIR/" 2>/dev/null || true
        fi

        if [[ -f ".env" ]]; then
            cp .env "$BACKUP_DIR/env_backup" 2>/dev/null || true
        fi

        log_success "Backup created at: $BACKUP_DIR"
    fi
}

# Build Docker image
build_image() {
    if [[ "$BUILD_IMAGE" == "true" ]]; then
        log_info "Building Docker image..."

        # Build base image
        docker build -t mcp-learning-server:latest .

        if [[ "$ENVIRONMENT" == "production" ]]; then
            docker tag mcp-learning-server:latest mcp-learning-server:production
            log_success "Production image built and tagged"
        fi

        log_success "Docker image built successfully"
    fi
}

# Pull latest images
pull_images() {
    if [[ "$PULL_LATEST" == "true" ]]; then
        log_info "Pulling latest images..."
        docker-compose pull
        log_success "Latest images pulled"
    fi
}

# Run tests
run_tests() {
    if [[ "$RUN_TESTS" == "true" ]]; then
        log_info "Running tests..."

        # Build test image
        docker build --target builder -t mcp-learning-server:test .

        # Run tests in container
        docker run --rm -v "$(pwd)/tests:/app/tests:ro" mcp-learning-server:test \
            python -m pytest tests/ -v --tb=short

        log_success "Tests completed successfully"
    fi
}

# Deploy services
deploy_services() {
    local compose_files="-f docker-compose.yml"

    if [[ "$ENVIRONMENT" == "production" ]]; then
        compose_files="$compose_files -f docker-compose.prod.yml"
    fi

    log_info "Deploying services with configuration: $compose_files"

    # Stop existing services
    docker-compose $compose_files down --remove-orphans

    # Deploy services
    docker-compose $compose_files up -d

    log_success "Services deployed successfully"
}

# Wait for services to be healthy
wait_for_services() {
    log_info "Waiting for services to be healthy..."

    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
            log_success "MCP server is healthy"
            break
        fi

        if [[ $attempt -eq $max_attempts ]]; then
            log_error "Services failed to become healthy after $max_attempts attempts"
            exit 1
        fi

        log_info "Attempt $attempt/$max_attempts - waiting for services..."
        sleep 10
        ((attempt++))
    done
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."

    # Check if containers are running
    if ! docker-compose ps --services --filter "status=running" | grep -q "mcp-server"; then
        log_error "MCP server container is not running"
        exit 1
    fi

    # Test health endpoint
    if ! curl -f -s http://localhost:8000/health > /dev/null; then
        log_error "Health check failed"
        exit 1
    fi

    # Test main endpoint
    if ! curl -f -s http://localhost:8000/ > /dev/null; then
        log_error "Main endpoint test failed"
        exit 1
    fi

    log_success "Deployment verification completed successfully"
}

# Cleanup old images
cleanup() {
    log_info "Cleaning up unused Docker images..."
    docker image prune -f
    log_success "Cleanup completed"
}

# Show deployment status
show_status() {
    log_info "Deployment Status:"
    echo "===================="
    docker-compose ps
    echo ""

    log_info "Service URLs:"
    echo "- MCP Server: http://localhost:8000"
    echo "- Health Check: http://localhost:8000/health"
    echo "- API Docs: http://localhost:8000/docs (if debug enabled)"

    if docker-compose ps --services | grep -q "grafana"; then
        echo "- Grafana: http://localhost:3000"
    fi

    if docker-compose ps --services | grep -q "prometheus"; then
        echo "- Prometheus: http://localhost:9090"
    fi
}

# Show logs
show_logs() {
    log_info "Recent logs from MCP server:"
    docker-compose logs --tail=20 mcp-server
}

# Main deployment flow
main() {
    log_info "=== MCP Learning Server Deployment ==="
    log_info "Environment: $ENVIRONMENT"
    log_info "Build Image: $BUILD_IMAGE"
    log_info "Pull Latest: $PULL_LATEST"
    log_info "Backup Data: $BACKUP_DATA"
    log_info "Run Tests: $RUN_TESTS"
    echo ""

    create_directories
    load_environment
    backup_data
    build_image
    pull_images
    run_tests
    deploy_services
    wait_for_services
    verify_deployment
    cleanup

    echo ""
    log_success "=== Deployment completed successfully! ==="
    echo ""

    show_status
    echo ""
    show_logs
}

# Handle script options
while [[ $# -gt 1 ]]; do
    key="$2"
    case $key in
        --no-build)
            BUILD_IMAGE="false"
            shift
            ;;
        --pull)
            PULL_LATEST="true"
            shift
            ;;
        --no-backup)
            BACKUP_DATA="false"
            shift
            ;;
        --test)
            RUN_TESTS="true"
            shift
            ;;
        *)
            log_warning "Unknown option: $key"
            shift
            ;;
    esac
done

# Run main function
main

# Trap errors
trap 'log_error "Deployment failed! Check the logs above for details."' ERR