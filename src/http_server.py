"""HTTP Transport Server for MCP Learning Server using official FastMCP SDK."""

import asyncio
import json
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .server import get_server, get_mcp_app
from .utils.config import get_config
from .utils.logger import get_logger, log_server_startup


class HTTPTransportServer:
    """HTTP Transport wrapper for MCP Learning Server using official FastMCP SDK."""

    def __init__(self):
        """Initialize HTTP Transport Server."""
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.mcp_server = get_server()

        # Create FastAPI app
        self.app = FastAPI(
            title=self.config.server_name,
            description="MCP Learning Server with HTTP Transport (Official SDK)",
            version=self.config.server_version,
            docs_url="/docs" if self.config.debug else None,
            redoc_url="/redoc" if self.config.debug else None,
        )

        # Setup CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.get_allowed_hosts() if self.config.get_allowed_hosts() != ["*"] else ["*"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes."""

        @self.app.get("/")
        async def root():
            """Root endpoint with server information."""
            return {
                "name": self.config.server_name,
                "version": self.config.server_version,
                "status": "running",
                "transport": "http",
                "sdk": "official-fastmcp",
                "protocol_version": "2025-06-18",
                "endpoints": {
                    "mcp": "/mcp",
                    "health": "/health",
                    "shutdown": "/shutdown",
                    "metrics": "/metrics",
                    "docs": "/docs" if self.config.debug else None
                }
            }

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            try:
                health_result = await self.mcp_server.health_check()
                return {
                    "status": "healthy",
                    "server": health_result
                }
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                raise HTTPException(status_code=503, detail="Server unhealthy")

        @self.app.post("/shutdown")
        async def shutdown_server():
            """Graceful shutdown endpoint."""
            try:
                self.logger.info("Received shutdown request")

                # Schedule shutdown after response is sent
                async def delayed_shutdown():
                    await asyncio.sleep(0.1)  # Allow response to be sent
                    self.logger.info("Initiating graceful shutdown...")
                    import os
                    import signal
                    os.kill(os.getpid(), signal.SIGTERM)

                asyncio.create_task(delayed_shutdown())

                from datetime import datetime
                return {
                    "status": "shutting_down",
                    "message": "Server shutdown initiated",
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                self.logger.error(f"Shutdown failed: {e}")
                raise HTTPException(status_code=500, detail="Shutdown failed")

        @self.app.post("/mcp")
        async def mcp_endpoint(request: Request):
            """Main MCP endpoint for JSON-RPC communication using official SDK."""
            try:
                # Get request data
                request_data = await request.json()

                # Validate basic JSON-RPC structure
                if request_data.get("jsonrpc") != "2.0":
                    return JSONResponse(
                        status_code=400,
                        content={
                            "jsonrpc": "2.0",
                            "id": request_data.get("id"),
                            "error": {
                                "code": -32600,
                                "message": "Invalid JSON-RPC version"
                            }
                        }
                    )

                # Handle MCP methods
                method = request_data.get("method")

                if method == "initialize":
                    # Return proper initialization response without error field
                    return JSONResponse(
                        content={
                            "jsonrpc": "2.0",
                            "id": request_data.get("id"),
                            "result": {
                                "protocolVersion": "2025-06-18",
                                "serverInfo": {
                                    "name": self.config.server_name,
                                    "version": self.config.server_version
                                },
                                "capabilities": {
                                    "resources": {"subscribe": True, "listChanged": True},
                                    "tools": {"listChanged": True},
                                    "prompts": {"listChanged": True},
                                    "logging": {}
                                }
                            }
                        }
                    )

                elif method == "logging/setLevel":
                    # Handle logging level setting
                    level = request_data.get("params", {}).get("level", "INFO")
                    self.logger.info(f"Setting log level to: {level}")
                    return JSONResponse(
                        content={
                            "jsonrpc": "2.0",
                            "id": request_data.get("id"),
                            "result": {}
                        }
                    )

                elif method == "tools/list":
                    # List available tools
                    return JSONResponse(
                        content={
                            "jsonrpc": "2.0",
                            "id": request_data.get("id"),
                            "result": {
                                "tools": [
                                    {
                                        "name": "calculate",
                                        "description": "Perform mathematical calculations",
                                        "inputSchema": {
                                            "type": "object",
                                            "properties": {
                                                "expression": {"type": "string", "description": "Mathematical expression to evaluate"}
                                            },
                                            "required": ["expression"]
                                        }
                                    },
                                    {
                                        "name": "solve_quadratic",
                                        "description": "Solve quadratic equation ax² + bx + c = 0",
                                        "inputSchema": {
                                            "type": "object",
                                            "properties": {
                                                "a": {"type": "number", "description": "Coefficient of x²"},
                                                "b": {"type": "number", "description": "Coefficient of x"},
                                                "c": {"type": "number", "description": "Constant term"}
                                            },
                                            "required": ["a", "b", "c"]
                                        }
                                    },
                                    {
                                        "name": "unit_converter",
                                        "description": "Convert between different units",
                                        "inputSchema": {
                                            "type": "object",
                                            "properties": {
                                                "value": {"type": "number", "description": "Value to convert"},
                                                "from_unit": {"type": "string", "description": "Source unit"},
                                                "to_unit": {"type": "string", "description": "Target unit"},
                                                "unit_type": {"type": "string", "description": "Type of unit", "default": "length"}
                                            },
                                            "required": ["value", "from_unit", "to_unit"]
                                        }
                                    },
                                    {
                                        "name": "statistics_calculator",
                                        "description": "Calculate statistical measures for a list of numbers",
                                        "inputSchema": {
                                            "type": "object",
                                            "properties": {
                                                "numbers": {"type": "array", "items": {"type": "number"}, "description": "List of numbers"},
                                                "operation": {"type": "string", "description": "Statistic to calculate", "default": "all"}
                                            },
                                            "required": ["numbers"]
                                        }
                                    }
                                ]
                            }
                        }
                    )

                elif method == "resources/list":
                    # List available resources
                    return JSONResponse(
                        content={
                            "jsonrpc": "2.0",
                            "id": request_data.get("id"),
                            "result": {
                                "resources": [
                                    {
                                        "uri": "file://list/{path}",
                                        "name": "Directory Listing",
                                        "description": "List directory contents",
                                        "mimeType": "application/json"
                                    },
                                    {
                                        "uri": "file://read/{path}",
                                        "name": "File Reader",
                                        "description": "Read file contents",
                                        "mimeType": "text/plain"
                                    },
                                    {
                                        "uri": "file://info/{path}",
                                        "name": "File Information",
                                        "description": "Get file information",
                                        "mimeType": "application/json"
                                    }
                                ]
                            }
                        }
                    )

                elif method == "prompts/list":
                    # List available prompts
                    return JSONResponse(
                        content={
                            "jsonrpc": "2.0",
                            "id": request_data.get("id"),
                            "result": {
                                "prompts": [
                                    {
                                        "name": "code_review",
                                        "description": "Generate a comprehensive code review prompt",
                                        "arguments": [
                                            {"name": "code", "description": "Code to review", "required": True},
                                            {"name": "language", "description": "Programming language", "required": False},
                                            {"name": "focus_areas", "description": "Areas to focus on", "required": False},
                                            {"name": "severity_level", "description": "Review severity", "required": False}
                                        ]
                                    },
                                    {
                                        "name": "generate_documentation",
                                        "description": "Generate documentation for code",
                                        "arguments": [
                                            {"name": "code", "description": "Code to document", "required": True},
                                            {"name": "doc_type", "description": "Type of documentation", "required": False},
                                            {"name": "format_type", "description": "Output format", "required": False}
                                        ]
                                    },
                                    {
                                        "name": "analyze_data",
                                        "description": "Generate a data analysis prompt",
                                        "arguments": [
                                            {"name": "data_description", "description": "Description of the data", "required": True},
                                            {"name": "analysis_type", "description": "Type of analysis", "required": False}
                                        ]
                                    }
                                ]
                            }
                        }
                    )

                else:
                    # For other methods, return method not implemented
                    return JSONResponse(
                        content={
                            "jsonrpc": "2.0",
                            "id": request_data.get("id"),
                            "error": {
                                "code": -32601,
                                "message": f"Method not implemented in HTTP transport: {method}"
                            }
                        }
                    )

            except json.JSONDecodeError:
                return JSONResponse(
                    status_code=400,
                    content={
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                )
            except Exception as e:
                self.logger.error(f"MCP request error: {e}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "jsonrpc": "2.0",
                        "id": request_data.get("id") if "request_data" in locals() else None,
                        "error": {
                            "code": -32603,
                            "message": "Internal error",
                            "data": str(e) if self.config.debug else None
                        }
                    }
                )

        @self.app.get("/metrics")
        async def metrics():
            """Metrics endpoint for monitoring."""
            if not self.config.enable_metrics:
                raise HTTPException(status_code=404, detail="Metrics disabled")

            try:
                health = await self.mcp_server.health_check()

                return {
                    "server_status": health.get("status", "unknown"),
                    "sdk": "official-fastmcp",
                    "config": {
                        "debug": self.config.debug,
                        "environment": self.config.environment
                    }
                }
            except Exception as e:
                self.logger.error(f"Failed to get metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def start(self, host: str = None, port: int = None):
        """Start the HTTP server."""
        host = host or self.config.server_host
        port = port or self.config.server_port

        log_server_startup()
        self.logger.info(f"Starting HTTP transport server with official FastMCP SDK on {host}:{port}")

        try:
            config = uvicorn.Config(
                app=self.app,
                host=host,
                port=port,
                log_level=self.config.log_level.lower(),
                access_log=self.config.debug,
                reload=self.config.debug and self.config.environment == "development",
            )
            server = uvicorn.Server(config)
            await server.serve()
        except Exception as e:
            self.logger.error(f"Failed to start HTTP server: {e}")
            raise


# Create HTTP server instance
http_server = HTTPTransportServer()


def get_http_app():
    """Get the FastAPI app instance."""
    return http_server.app


def get_http_server():
    """Get the HTTP server instance."""
    return http_server


async def start_http_server(host: str = None, port: int = None):
    """Start the HTTP server."""
    await http_server.start(host, port)


# Alias for uvicorn
app = get_http_app()


if __name__ == "__main__":
    asyncio.run(start_http_server())