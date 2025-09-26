#!/bin/bash
#
# MCP Learning Server Control Script
# Simplifies starting and stopping the MCP server with proper environment setup.
#

set -euo pipefail  # Exit on errors, undefined vars, pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Environment setup
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)" 2>/dev/null || true
export PATH="$HOME/.local/bin:$PATH"

print_colored() {
    local color=$1
    shift
    echo -e "${color}$*${NC}"
}

print_usage() {
    cat << EOF
MCP Learning Server Control Script

Usage: $0 {start|stop|restart|status|logs|tools|config|login} [options]

Commands:
    start [transport] [options]    Start the server
    stop                          Stop the server
    restart [transport] [options] Restart the server
    status                        Check server status
    logs                          Show recent server logs
    tools                         List all available tools
    config [reload]              Show or reload tool configuration
    login [status|qrcode|interactive|clear|info]  Manage Xiaohongshu login

Transport options:
    stdio                         STDIO transport (default, redirects to HTTP)
    http                          HTTP transport

HTTP options:
    --host HOST                   Server host (default: localhost)
    --port PORT                   Server port (default: 8000)
    --config CONFIG              Custom tools configuration file

Tool management:
    --list-tools                 List all available tools
    --reload-config             Reload tools configuration

Login management:
    status                       Check current login status
    qrcode                       Get QR code for login (requires GUI)
    interactive                  Interactive login process
    clear                        Clear saved login session
    info                         Show cookie information

Examples:
    $0 start                      # Start with HTTP transport (default)
    $0 start http                 # Start with HTTP transport
    $0 start http --port 8080     # Start HTTP on custom port
    $0 start --config custom.json # Start with custom config
    $0 stop                       # Stop all server processes
    $0 restart http               # Restart with HTTP transport
    $0 status                     # Check if server is running
    $0 tools                      # List all available tools
    $0 config reload              # Reload tool configuration
    $0 login status               # Check Xiaohongshu login status
    $0 login interactive          # Start interactive login process
    $0 login clear                # Clear saved login session

EOF
}

setup_environment() {
    cd "$PROJECT_ROOT"

    if ! command -v uv &> /dev/null; then
        print_colored $RED "❌ uv not found. Please install uv first."
        exit 1
    fi

    if ! python --version | grep -q "3\.10\|3\.11\|3\.12"; then
        print_colored $YELLOW "⚠️  Python 3.10+ recommended. Current: $(python --version)"
    fi
}

check_server_status() {
    local http_port=${1:-8000}
    local http_host=${2:-localhost}

    # Check HTTP server
    if curl -s "http://${http_host}:${http_port}/health" &>/dev/null; then
        print_colored $GREEN "✅ HTTP server running on ${http_host}:${http_port}"
        return 0
    fi

    # Check for processes
    if pgrep -f "start_server.py" &>/dev/null; then
        print_colored $YELLOW "⚠️  Server processes found but HTTP not responding"
        return 1
    fi

    print_colored $RED "❌ No server processes running"
    return 1
}

start_server() {
    local transport=${1:-stdio}
    shift || true

    print_colored $BLUE "🚀 Starting MCP Learning Server..."
    print_colored $BLUE "Transport: $transport"

    setup_environment

    case $transport in
        stdio)
            print_colored $BLUE "📡 Starting STDIO transport server"
            exec uv run python scripts/start_server.py --transport stdio "$@"
            ;;
        http)
            print_colored $BLUE "🌐 Starting HTTP transport server"
            exec uv run python scripts/start_server.py --transport http "$@"
            ;;
        *)
            print_colored $RED "❌ Unknown transport: $transport"
            print_colored $YELLOW "Valid transports: stdio, http"
            exit 1
            ;;
    esac
}

stop_server() {
    print_colored $BLUE "🛑 Stopping MCP Learning Server..."
    setup_environment

    if uv run python scripts/stop_server.py "$@"; then
        print_colored $GREEN "✅ Server stopped successfully"
        return 0
    else
        print_colored $RED "❌ Failed to stop server"
        return 1
    fi
}

restart_server() {
    print_colored $BLUE "🔄 Restarting MCP Learning Server..."

    # Stop server first
    stop_server
    sleep 2

    # Start server
    start_server "$@"
}

show_status() {
    print_colored $BLUE "📊 MCP Learning Server Status"
    print_colored $BLUE "=" $(printf '=%.0s' {1..50})

    check_server_status

    # Show process information
    if pgrep -f "start_server.py" &>/dev/null; then
        echo
        print_colored $BLUE "🔍 Running processes:"
        pgrep -f "start_server.py" | xargs ps -f -p 2>/dev/null || true
    fi

    # Show port usage
    echo
    print_colored $BLUE "🔌 Port 8000 usage:"
    netstat -tlnp 2>/dev/null | grep ":8000 " || echo "Port 8000 not in use"
}

show_logs() {
    print_colored $BLUE "📋 Recent Server Logs"
    print_colored $BLUE "=" $(printf '=%.0s' {1..50})

    # Show recent logs from system journal if available
    if command -v journalctl &> /dev/null; then
        journalctl --user-unit=mcp-server -n 50 --no-pager 2>/dev/null || true
    fi

    # Show logs from common locations
    local log_files=(
        "/tmp/mcp-server.log"
        "$HOME/.local/share/mcp-server/logs/server.log"
        "$PROJECT_ROOT/logs/server.log"
    )

    for log_file in "${log_files[@]}"; do
        if [[ -f "$log_file" ]]; then
            print_colored $BLUE "📄 Log file: $log_file"
            tail -n 20 "$log_file" 2>/dev/null || true
            echo
        fi
    done

    print_colored $YELLOW "💡 Tip: For real-time logs, run the server in foreground mode"
}

list_tools() {
    print_colored $BLUE "🔧 Available Tools"
    print_colored $BLUE "=" $(printf '=%.0s' {1..50})

    setup_environment

    if uv run python scripts/start_server.py --list-tools; then
        print_colored $GREEN "✅ Tools list completed"
    else
        print_colored $RED "❌ Failed to list tools"
        return 1
    fi
}

manage_config() {
    local action=${1:-show}

    print_colored $BLUE "⚙️  Tool Configuration Management"
    print_colored $BLUE "=" $(printf '=%.0s' {1..50})

    setup_environment

    case $action in
        reload)
            print_colored $BLUE "🔄 Reloading tool configuration..."
            if uv run python scripts/start_server.py --reload-config; then
                print_colored $GREEN "✅ Configuration reloaded successfully"
            else
                print_colored $RED "❌ Failed to reload configuration"
                return 1
            fi
            ;;
        show|*)
            print_colored $BLUE "📋 Current tool configuration:"
            echo
            print_colored $BLUE "Configuration file location:"
            print_colored $YELLOW "  $PROJECT_ROOT/src/config/tools.json"
            echo
            print_colored $BLUE "To view or edit configuration:"
            print_colored $YELLOW "  cat $PROJECT_ROOT/src/config/tools.json"
            print_colored $YELLOW "  $0 config reload  # After making changes"
            echo
            print_colored $BLUE "Available tools:"
            uv run python scripts/start_server.py --list-tools 2>/dev/null | grep -E "^  [✓✗]" || true
            ;;
    esac
}

manage_login() {
    local action=${1:-status}

    print_colored $BLUE "🔑 Xiaohongshu Login Management"
    print_colored $BLUE "=" $(printf '=%.0s' {1..50})

    setup_environment

    case $action in
        status)
            print_colored $BLUE "🔍 Checking login status..."
            if uv run python scripts/login.py --status --headless; then
                print_colored $GREEN "✅ You are currently logged in"
            else
                print_colored $YELLOW "⚠️  You are not logged in"
                print_colored $BLUE "💡 To login, run: $0 login interactive"
            fi
            ;;
        interactive)
            print_colored $BLUE "🚀 Starting interactive login process..."
            uv run python scripts/login.py --login
            ;;
        clear)
            print_colored $BLUE "🧹 Clearing saved login session..."
            if uv run python scripts/login.py --clear; then
                print_colored $GREEN "✅ Login session cleared successfully"
            else
                print_colored $RED "❌ Failed to clear login session"
                return 1
            fi
            ;;
        info)
            print_colored $BLUE "📊 Cookie information:"
            uv run python scripts/login.py --info
            ;;
        qrcode)
            print_colored $BLUE "📱 Getting QR code for login..."
            print_colored $YELLOW "⚠️  This feature requires a GUI environment"
            print_colored $BLUE "💡 For headless environments, use: $0 login interactive"
            # This would require implementing QR code display in the login script
            print_colored $RED "❌ QR code display not yet implemented in CLI"
            print_colored $BLUE "🔄 Use interactive mode instead: $0 login interactive"
            ;;
        *)
            # print_colored $RED "❌ Unknown login action: $action"
            # echo
            # print_colored $BLUE "Available login actions:"
            # print_colored $YELLOW "  status      - Check current login status"
            # print_colored $YELLOW "  interactive - Start interactive login process"
            # print_colored $YELLOW "  clear       - Clear saved login session"
            # print_colored $YELLOW "  info        - Show cookie information"
            # print_colored $YELLOW "  qrcode      - Get QR code (GUI required)"
            print_colored $BLUE "📊 default login:"
            uv run python scripts/login.py "$@"
            ;;
    esac
}

# Main command processing
case "${1:-}" in
    start)
        shift
        start_server "$@"
        ;;
    stop)
        shift
        stop_server "$@"
        ;;
    restart)
        shift
        restart_server "$@"
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    tools)
        list_tools
        ;;
    config)
        shift
        manage_config "$@"
        ;;
    login)
        shift
        manage_login "$@"
        ;;
    -h|--help|help)
        print_usage
        ;;
    *)
        print_colored $RED "❌ Unknown command: ${1:-}"
        echo
        print_usage
        exit 1
        ;;
esac