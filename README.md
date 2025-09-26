# MCP Learning Server

A comprehensive Model Context Protocol (MCP) server with dynamic tool registry, featuring advanced social media automation and mathematical computation capabilities.

## 🎯 Project Overview

This project demonstrates modern MCP server architecture with a dynamic tool registration system. It supports multiple tool providers, configurable tool management, and provides both computational tools and social media automation capabilities.

## 🏗️ Architecture

Built with a clean, scalable architecture featuring:

- **Dynamic Tool Registry**: Runtime tool registration and management
- **Tool Providers**: Modular tool organization by functionality
- **Configuration Management**: JSON-based tool configuration with hot reload
- **HTTP Transport**: Production-ready HTTP server with JSON-RPC support
- **Error Handling**: Comprehensive error handling with retry mechanisms

### Core Components

- `src/core/tool_registry.py` - Central tool management system
- `src/core/tool_providers.py` - Tool provider implementations
- `src/config/tools_config.py` - Configuration management
- `src/http_server.py` - HTTP transport server
- `src/config/tools.json` - Tool configuration file

## 🚀 Features

### Available Tools (13 tools across 2 categories)

#### Calculator Tools (4 tools)
- **calculate**: Perform mathematical calculations
- **solve_quadratic**: Solve quadratic equations ax² + bx + c = 0
- **unit_converter**: Convert between different units
- **statistics_calculator**: Calculate statistical measures

#### Xiaohongshu Tools (9 tools)
- **check_login_status**: Check Xiaohongshu login status
- **get_login_qrcode**: Get login QR code for authentication
- **wait_for_login**: Wait for user to complete login process
- **publish_content**: Publish text/image content to Xiaohongshu
- **list_feeds**: Get recommended feed list from homepage
- **search_feeds**: Search content by keyword
- **get_feed_detail**: Get detailed post information
- **post_comment_to_feed**: Post comments to specific posts
- **user_profile**: Get user profile information

### Resources
- **File Manager**: Browse and read files from the file system
- **System Info**: Get system information and resource usage

### Prompts
- **Code Review**: Template for comprehensive code analysis
- **Documentation**: Generate documentation for code
- **Data Analysis**: Analyze data with customizable approaches
- **Documentation**: Template for generating documentation
- **Data Analysis**: Template for analyzing datasets

## 📋 Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## 🛠️ Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd mcp_learn_py

# Install dependencies
uv sync

# Or install with development dependencies
uv sync --dev
```

### Using pip

```bash
# Clone the repository
git clone <your-repo-url>
cd mcp_learn_py

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or install development dependencies
pip install -r requirements-dev.txt
```

## ⚙️ Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your preferred settings:
   ```bash
   MCP_SERVER_NAME="My MCP Server"
   MCP_SERVER_PORT="8000"
   DEBUG="true"
   # ... other settings
   ```

## 🏃‍♂️ Running the Server

### Development Mode

```bash
# Using uv
uv run python scripts/start_server.py

# Using pip
python scripts/start_server.py
```

### Production Mode

```bash
# Using uvicorn directly
uvicorn src.server:app --host 0.0.0.0 --port 8000

# Or using the configured script
mcp-server
```

The server will start on `http://localhost:8000` by default.

## 🔑 Xiaohongshu Login Management

The framework now includes comprehensive login management with cookie persistence:

### Interactive Login

```bash
# Check current login status
./scripts/mcp_server.sh login status

# Start interactive login process
./scripts/mcp_server.sh login interactive

# Get cookie information
./scripts/mcp_server.sh login info

# Clear saved login session
./scripts/mcp_server.sh login clear
```

### Direct Login Script

```bash
# Using the login script directly
uv run python scripts/login.py --status      # Check status
uv run python scripts/login.py --login       # Interactive login
uv run python scripts/login.py --clear       # Clear session
uv run python scripts/login.py --info        # Show cookie info
```

### Key Features

- **Cookie Persistence**: Login sessions are automatically saved and restored
- **QR Code Support**: Get login QR codes for mobile authentication
- **Reliable Detection**: Uses precise selectors for accurate login status checking
- **Cross-platform**: Works on Windows, macOS, and Linux
- **Multiple Methods**: Interactive login, QR code, or manual browser login

### MCP Tools for Login

- `check_login_status` - Check if logged into Xiaohongshu
- `get_login_qrcode` - Get QR code image for mobile login
- `wait_for_login` - Wait for login completion with timeout

## 🧪 Testing

### Run Tests

```bash
# Using uv
uv run pytest

# Using pip
pytest

# With coverage
pytest --cov=src --cov-report=html
```

### Manual Testing

Use the included test client:

```bash
# Using uv
uv run python scripts/test_client.py

# Using pip
python scripts/test_client.py

# Or using the script
mcp-test-client
```

## 📖 Usage Examples

### Connecting from Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "mcp-learning-server": {
      "command": "uv",
      "args": ["run", "python", "/path/to/mcp_learn_py/scripts/start_server.py"],
      "env": {
        "UV_PROJECT_ENVIRONMENT": "/path/to/mcp_learn_py/.venv"
      }
    }
  }
}
```

### Remote Deployment

The server supports HTTP transport for remote deployment. See [docs/deployment.md](docs/deployment.md) for detailed instructions.

## 🔧 Development

### Code Style

This project uses:
- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

```bash
# Format code
uv run black src/ tests/
uv run isort src/ tests/

# Lint code
uv run flake8 src/ tests/

# Type check
uv run mypy src/
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run hooks manually
uv run pre-commit run --all-files
```

## 📚 Learning Resources

- [MCP Official Documentation](https://modelcontextprotocol.io/)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if needed
5. Run the test suite (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Anthropic](https://anthropic.com) for creating the Model Context Protocol
- The MCP community for examples and documentation
- Contributors to the MCP ecosystem