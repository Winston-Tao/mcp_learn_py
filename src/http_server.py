"""HTTP Transport Server with Dynamic Tool Registry"""

import asyncio
import json
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .server import get_server
from .utils.config import get_config
from .utils.logger import get_logger, log_server_startup
from .core.tool_registry import get_tool_registry
from .core.tool_providers import CalculatorToolProvider, XiaohongshuToolProvider


class HTTPTransportServer:
    """HTTP Transport Server with Dynamic Tool Registry"""

    def __init__(self):
        """Initialize HTTP Transport Server."""
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.mcp_server = get_server()
        self.tool_registry = get_tool_registry()

        # 初始化工具提供者
        self._initialize_tool_providers()

        # Create FastAPI app
        self.app = FastAPI(
            title=self.config.server_name,
            description="MCP Learning Server with Dynamic Tool Registry",
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

    def _initialize_tool_providers(self):
        """初始化工具提供者"""
        try:
            # 注册计算器工具提供者
            calc_provider = CalculatorToolProvider(self.mcp_server)
            self.tool_registry.register_provider("calculator", calc_provider)

            # 注册小红书工具提供者
            xhs_provider = XiaohongshuToolProvider(self.mcp_server)
            self.tool_registry.register_provider("xiaohongshu", xhs_provider)

            self.logger.info(f"Initialized tool providers. Total tools: {self.tool_registry.get_tool_count()}")

            # 记录所有类别
            categories = self.tool_registry.get_categories()
            self.logger.info(f"Available tool categories: {categories}")

        except Exception as e:
            self.logger.error(f"Failed to initialize tool providers: {e}")
            raise

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
                "architecture": "dynamic-tool-registry",
                "protocol_version": "2025-06-18",
                "tool_stats": {
                    "total_tools": self.tool_registry.get_tool_count(),
                    "categories": self.tool_registry.get_categories()
                },
                "endpoints": {
                    "mcp": "/mcp",
                    "health": "/health",
                    "shutdown": "/shutdown",
                    "metrics": "/metrics",
                    "tools": "/tools",
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
                    "server": health_result,
                    "tools": {
                        "total": self.tool_registry.get_tool_count(),
                        "categories": self.tool_registry.get_categories()
                    }
                }
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                raise HTTPException(status_code=503, detail="Server unhealthy")

        @self.app.get("/tools")
        async def list_tools(category: Optional[str] = None):
            """List available tools (REST endpoint)."""
            try:
                tools = self.tool_registry.get_tool_schemas(category)
                return {
                    "tools": tools,
                    "total": len(tools),
                    "category": category,
                    "available_categories": self.tool_registry.get_categories()
                }
            except Exception as e:
                self.logger.error(f"Failed to list tools: {e}")
                raise HTTPException(status_code=500, detail=str(e))

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
            """Main MCP endpoint for JSON-RPC communication using dynamic tool registry."""
            try:
                # Get request data
                request_data = await request.json()

                # Log the complete request for debugging
                self.logger.info(f"MCP Request received:")
                self.logger.info(f"  Method: {request_data.get('method')}")
                self.logger.info(f"  ID: {request_data.get('id')}")
                if self.config.debug:
                    self.logger.info(f"  Full Request: {request_data}")

                # Validate basic JSON-RPC structure
                if request_data.get("jsonrpc") != "2.0":
                    return self._json_rpc_error_response(
                        request_data.get("id"),
                        -32600,
                        "Invalid JSON-RPC version"
                    )

                # Handle MCP methods
                method = request_data.get("method")

                if method == "initialize":
                    return self._json_rpc_success_response(
                        request_data.get("id"),
                        {
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
                    )

                elif method == "logging/setLevel":
                    level = request_data.get("params", {}).get("level", "INFO")
                    self.logger.info(f"Setting log level to: {level}")
                    return self._json_rpc_success_response(request_data.get("id"), {})

                elif method == "tools/list":
                    # 使用动态工具注册管理器
                    tools = self.tool_registry.get_tool_schemas()
                    return self._json_rpc_success_response(
                        request_data.get("id"),
                        {"tools": tools}
                    )

                elif method == "tools/call":
                    return await self._handle_tool_call(request_data)

                elif method == "resources/list":
                    # 资源列表保持不变
                    return self._json_rpc_success_response(
                        request_data.get("id"),
                        {
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
                    )

                elif method == "prompts/list":
                    # 提示列表保持不变
                    return self._json_rpc_success_response(
                        request_data.get("id"),
                        {
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
                    )

                else:
                    return self._json_rpc_error_response(
                        request_data.get("id"),
                        -32601,
                        f"Method not implemented: {method}"
                    )

            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error: {e}")
                return self._json_rpc_error_response(None, -32700, "Parse error")
            except Exception as e:
                self.logger.error(f"MCP request error: {e}")
                return self._json_rpc_error_response(
                    request_data.get("id") if "request_data" in locals() else None,
                    -32603,
                    "Internal error",
                    str(e) if self.config.debug else None
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
                    "version": self.config.server_version,
                    "architecture": "dynamic-tool-registry",
                    "tools": {
                        "total": self.tool_registry.get_tool_count(),
                        "categories": self.tool_registry.get_categories(),
                        "by_category": {
                            cat: len(self.tool_registry.get_tools_by_category(cat))
                            for cat in self.tool_registry.get_categories()
                        }
                    },
                    "config": {
                        "debug": self.config.debug,
                        "environment": self.config.environment
                    }
                }
            except Exception as e:
                self.logger.error(f"Failed to get metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def _handle_tool_call(self, request_data: Dict[str, Any]) -> JSONResponse:
        """处理工具调用"""
        try:
            params = request_data.get("params", {})
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            self.logger.info(f"Tool call: {tool_name} with args: {tool_args}")

            if not self.tool_registry.is_tool_registered(tool_name):
                return self._json_rpc_error_response(
                    request_data.get("id"),
                    -32601,
                    f"Unknown tool: {tool_name}"
                )

            # 使用工具注册管理器调用工具
            result = await self.tool_registry.call_tool(tool_name, tool_args)

            return self._json_rpc_success_response(request_data.get("id"), result)

        except Exception as e:
            self.logger.error(f"Tool execution error: {e}")
            return self._json_rpc_error_response(
                request_data.get("id"),
                -32603,
                f"Tool execution failed: {str(e)}"
            )

    def _json_rpc_success_response(self, request_id: Any, result: Any) -> JSONResponse:
        """生成JSON-RPC成功响应"""
        response_content = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
        return JSONResponse(content=response_content)

    def _json_rpc_error_response(self, request_id: Any, error_code: int, message: str, data: Any = None) -> JSONResponse:
        """生成JSON-RPC错误响应"""
        error_response = {
            "code": error_code,
            "message": message
        }
        if data is not None:
            error_response["data"] = data

        response_content = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error_response
        }
        return JSONResponse(content=response_content)

    async def start(self, host: str = None, port: int = None):
        """Start the HTTP server."""
        host = host or self.config.server_host
        port = port or self.config.server_port

        log_server_startup()
        self.logger.info(f"Starting HTTP transport server with dynamic tool registry on {host}:{port}")
        self.logger.info(f"Tool registry initialized with {self.tool_registry.get_tool_count()} tools")

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