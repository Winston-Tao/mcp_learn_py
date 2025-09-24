"""Logging configuration for MCP Learning Server."""

import logging
import sys
from typing import Optional

import structlog
from structlog.stdlib import LoggerFactory

from .config import get_config


def configure_logging() -> None:
    """Configure structured logging for the application."""
    config = get_config()

    # Configure log level
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=config.debug) if config.debug else structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance.

    Args:
        name: Optional logger name. If not provided, uses the calling module's name.

    Returns:
        structlog.stdlib.BoundLogger: Configured logger instance.
    """
    if name is None:
        # Get the calling module's name
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            name = frame.f_back.f_globals.get('__name__', 'unknown')
        else:
            name = 'unknown'

    return structlog.get_logger(name)


def log_server_startup() -> None:
    """Log server startup information."""
    config = get_config()
    logger = get_logger(__name__)

    logger.info(
        "Starting MCP Learning Server",
        server_name=config.server_name,
        version=config.server_version,
        host=config.server_host,
        port=config.server_port,
        environment=config.environment,
        debug=config.debug,
        log_level=config.log_level,
    )


def log_server_shutdown() -> None:
    """Log server shutdown information."""
    logger = get_logger(__name__)
    logger.info("MCP Learning Server shutting down")


class LoggerAdapter:
    """Adapter to make structlog compatible with standard library logging interfaces."""

    def __init__(self, logger: structlog.stdlib.BoundLogger):
        self.logger = logger

    def info(self, message: str, **kwargs) -> None:
        """Log info level message."""
        self.logger.info(message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug level message."""
        self.logger.debug(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning level message."""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error level message."""
        self.logger.error(message, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback."""
        self.logger.exception(message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical level message."""
        self.logger.critical(message, **kwargs)


def get_logger_adapter(name: Optional[str] = None) -> LoggerAdapter:
    """Get a logger adapter for compatibility with standard library logging.

    Args:
        name: Optional logger name.

    Returns:
        LoggerAdapter: Configured logger adapter.
    """
    logger = get_logger(name)
    return LoggerAdapter(logger)