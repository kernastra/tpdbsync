#!/bin/bash

# Docker management script for TPDB Poster Sync

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
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

# Check if docker and docker-compose are available
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    log_success "Docker dependencies found"
}

# Setup environment file
setup_env() {
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_success "Created .env file from .env.example"
            log_warning "Please edit .env file with your settings"
        else
            log_error ".env.example not found"
            exit 1
        fi
    else
        log_info ".env file already exists"
    fi
}

# Build the Docker image
build_image() {
    log_info "Building Docker image..."
    docker-compose build
    log_success "Docker image built successfully"
}

# Start the service
start_service() {
    log_info "Starting TPDB Poster Sync service..."
    docker-compose up -d
    log_success "Service started"
    
    # Show status
    docker-compose ps
}

# Stop the service
stop_service() {
    log_info "Stopping TPDB Poster Sync service..."
    docker-compose down
    log_success "Service stopped"
}

# Restart the service
restart_service() {
    log_info "Restarting TPDB Poster Sync service..."
    docker-compose restart
    log_success "Service restarted"
}

# Show logs
show_logs() {
    local follow=${1:-false}
    
    if [ "$follow" = "true" ]; then
        log_info "Following logs (Ctrl+C to exit)..."
        docker-compose logs -f
    else
        log_info "Showing recent logs..."
        docker-compose logs --tail=50
    fi
}

# Run management commands
run_command() {
    local cmd="$1"
    shift
    
    case "$cmd" in
        "test-config")
            docker-compose exec tpdb-poster-sync python manage.py validate-config
            ;;
        "test-connection")
            docker-compose exec tpdb-poster-sync python manage.py test-connection
            ;;
        "scan-local")
            docker-compose exec tpdb-poster-sync python manage.py scan-local
            ;;
        "dry-run")
            docker-compose exec tpdb-poster-sync python main.py --dry-run
            ;;
        "shell")
            docker-compose exec tpdb-poster-sync bash
            ;;
        *)
            log_error "Unknown command: $cmd"
            echo "Available commands: test-config, test-connection, scan-local, dry-run, shell"
            exit 1
            ;;
    esac
}

# Show service status
show_status() {
    log_info "Service status:"
    docker-compose ps
    
    echo ""
    log_info "Resource usage:"
    docker stats --no-stream tpdb-poster-sync 2>/dev/null || log_warning "Service not running"
}

# Clean up (remove containers and images)
cleanup() {
    log_warning "This will remove containers and images. Continue? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        log_info "Cleaning up..."
        docker-compose down --rmi all --volumes --remove-orphans
        log_success "Cleanup complete"
    else
        log_info "Cleanup cancelled"
    fi
}

# Show help
show_help() {
    echo "TPDB Poster Sync Docker Management Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  setup         - Initial setup (create .env file)"
    echo "  build         - Build Docker image"
    echo "  start         - Start the service"
    echo "  stop          - Stop the service"
    echo "  restart       - Restart the service"
    echo "  status        - Show service status"
    echo "  logs          - Show recent logs"
    echo "  logs-follow   - Follow logs in real-time"
    echo "  cmd <command> - Run management command"
    echo "  cleanup       - Remove containers and images"
    echo "  help          - Show this help"
    echo ""
    echo "Management commands (use with 'cmd'):"
    echo "  test-config     - Validate configuration"
    echo "  test-connection - Test server connection"
    echo "  scan-local      - Scan local poster directories"
    echo "  dry-run         - Perform dry run sync"
    echo "  shell           - Open interactive shell"
    echo ""
    echo "Examples:"
    echo "  $0 setup"
    echo "  $0 build"
    echo "  $0 start"
    echo "  $0 cmd test-config"
    echo "  $0 logs-follow"
}

# Main command processing
main() {
    case "${1:-help}" in
        "setup")
            check_dependencies
            setup_env
            ;;
        "build")
            check_dependencies
            build_image
            ;;
        "start")
            check_dependencies
            start_service
            ;;
        "stop")
            check_dependencies
            stop_service
            ;;
        "restart")
            check_dependencies
            restart_service
            ;;
        "status")
            check_dependencies
            show_status
            ;;
        "logs")
            check_dependencies
            show_logs false
            ;;
        "logs-follow")
            check_dependencies
            show_logs true
            ;;
        "cmd")
            check_dependencies
            if [ $# -lt 2 ]; then
                log_error "Command required"
                show_help
                exit 1
            fi
            run_command "${@:2}"
            ;;
        "cleanup")
            check_dependencies
            cleanup
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
