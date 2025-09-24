"""MCP Resources module.

Resources are endpoints that expose data or information to MCP clients.
They are read-only and similar to GET requests in REST APIs.
"""

from .file_manager import FileManagerResource
from .system_info import SystemInfoResource

__all__ = [
    "FileManagerResource",
    "SystemInfoResource",
]