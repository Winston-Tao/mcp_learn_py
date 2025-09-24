# MCP Learning Server

A comprehensive Model Context Protocol (MCP) server implementation for learning and understanding MCP's core concepts and architecture.

## 🎯 Project Overview

This project is designed to help developers understand the Model Context Protocol (MCP) by providing a complete, well-documented server implementation. It demonstrates all key MCP concepts including Resources, Tools, and Prompts through practical examples.

## 🏗️ Architecture

MCP enables AI applications to connect with external systems through a standardized protocol. This server demonstrates:

- **Resources**: Read-only data endpoints (like REST GET requests)
- **Tools**: Functions that perform actions or computations
- **Prompts**: Reusable templates for LLM interactions
- **HTTP Transport**: Remote server deployment capability

## 🚀 Features

### Resources
- **File Manager**: Browse and read files from the file system
- **System Info**: Get system information and resource usage

### Tools
- **Calculator**: Perform mathematical calculations
- **File Operations**: Create, read, update, and delete files
- **Web Scraper**: Extract content from web pages

### Prompts
- **Code Review**: Template for code analysis
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