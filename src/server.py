"""Main MCP Learning Server implementation using official FastMCP SDK."""

import asyncio
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP
from mcp.server.models import InitializationOptions
import mcp.types as types

from .utils.config import get_config
from .utils.logger import configure_logging, get_logger, log_server_startup


class MCPLearningServer:
    """MCP Learning Server using official FastMCP SDK."""

    def __init__(self):
        """Initialize the MCP Learning Server."""
        # Configure logging first
        configure_logging()
        self.logger = get_logger(__name__)

        # Load configuration
        self.config = get_config()

        # Initialize FastMCP server with official SDK
        self.mcp = FastMCP(
            name=self.config.server_name,
        )

        self.logger.info("MCP Learning Server initialized with official FastMCP SDK",
                        name=self.config.server_name)

    async def start(self) -> None:
        """Start the MCP server using official SDK."""
        log_server_startup()

        try:
            # Use official SDK's run method which handles all protocol details
            async with self.mcp:
                await self.mcp.run(
                    options=InitializationOptions(
                        server_name=self.config.server_name,
                        server_version=self.config.server_version,
                    )
                )
        except Exception as e:
            self.logger.error("Failed to start server", error=str(e), exc_info=True)
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            "status": "healthy",
            "server_name": self.config.server_name,
            "version": self.config.server_version,
            "sdk": "official-fastmcp",
            "environment": self.config.environment,
            "debug": self.config.debug,
        }


# Create the main server instance
server = MCPLearningServer()


# Global functions for compatibility
def get_server() -> MCPLearningServer:
    """Get the main server instance."""
    return server


def get_mcp_app():
    """Get the FastMCP app instance for direct access."""
    return server.mcp


# Compatibility alias for external access
app = get_mcp_app()


async def main():
    """Main entry point for the server."""
    config = get_config()

    # Import and register all handlers with the official SDK
    from .resources import FileManagerResource, SystemInfoResource
    from .tools import CalculatorTool, FileOperationsTool, WebScraperTool
    from .prompts import PromptTemplates

    # Register components with the MCP server
    # Components will register themselves using @mcp.tool(), @mcp.resource(), etc.
    file_manager = FileManagerResource(server)
    system_info = SystemInfoResource(server)
    calculator = CalculatorTool(server)
    file_ops = FileOperationsTool(server)
    web_scraper = WebScraperTool(server)
    prompts = PromptTemplates(server)

    # Register handlers using the new official SDK pattern
    await file_manager.register()
    await system_info.register()
    await calculator.register()
    await file_ops.register()
    await web_scraper.register()
    await prompts.register()

    # Start server with official SDK
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())