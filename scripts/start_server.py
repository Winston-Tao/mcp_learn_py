#!/usr/bin/env python3
"""Start script for MCP Learning Server."""

import argparse
import asyncio
import signal
import sys
from pathlib import Path

# Add src directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.server import main as start_stdio_server
from src.http_server import start_http_server
from src.utils.logger import get_logger, log_server_shutdown
from src.utils.config import get_config


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger = get_logger(__name__)
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    log_server_shutdown()
    sys.exit(0)


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MCP Learning Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_server.py                    # Start with stdio transport (default)
  python start_server.py --transport http  # Start with HTTP transport
  python start_server.py --transport http --host 0.0.0.0 --port 8080
        """
    )

    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport protocol to use (default: stdio)"
    )

    parser.add_argument(
        "--host",
        type=str,
        help="Server host (only for HTTP transport)"
    )

    parser.add_argument(
        "--port",
        type=int,
        help="Server port (only for HTTP transport)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="MCP Learning Server 0.1.0"
    )

    return parser.parse_args()


async def start_server_with_transport(transport: str, host: str = None, port: int = None):
    """Start the server with specified transport."""
    setup_signal_handlers()
    config = get_config()
    logger = get_logger(__name__)

    try:
        if transport == "stdio":
            logger.info("Starting MCP server with STDIO transport")
            await start_stdio_server()
        elif transport == "http":
            logger.info(f"Starting MCP server with HTTP transport")
            await start_http_server(host=host, port=port)
        else:
            raise ValueError(f"Unknown transport: {transport}")

    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")
        log_server_shutdown()
    except Exception as e:
        logger.error("Server startup failed", error=str(e), exc_info=True)
        sys.exit(1)


def main():
    """Main entry point."""
    # Check Python version
    if sys.version_info < (3, 9):
        print("Error: Python 3.9 or higher is required")
        sys.exit(1)

    # Parse arguments
    args = parse_arguments()

    # Validate arguments
    if args.transport == "http":
        if args.host is None:
            config = get_config()
            args.host = config.server_host
        if args.port is None:
            config = get_config()
            args.port = config.server_port
    elif args.host or args.port:
        print("Warning: --host and --port are only used with HTTP transport")

    # Set debug mode if requested
    if args.debug:
        import os
        os.environ["DEBUG"] = "true"

    # Print startup information
    print(f"MCP Learning Server")
    print(f"Transport: {args.transport}")
    if args.transport == "http":
        print(f"Address: http://{args.host}:{args.port}")
    print(f"Press Ctrl+C to stop")
    print("-" * 50)

    # Run the server
    asyncio.run(start_server_with_transport(args.transport, args.host, args.port))


if __name__ == "__main__":
    main()