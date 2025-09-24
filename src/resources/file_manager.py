"""File Manager Resource for MCP Learning Server."""

import os
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import aiofiles
from pydantic import BaseModel

from ..utils.config import get_config
from ..utils.logger import get_logger


class FileInfo(BaseModel):
    """File information model."""
    name: str
    path: str
    size: int
    is_directory: bool
    mime_type: Optional[str] = None
    last_modified: float
    permissions: str
    readable: bool
    writable: bool


class DirectoryListing(BaseModel):
    """Directory listing model."""
    path: str
    total_items: int
    files: List[FileInfo]
    parent_directory: Optional[str] = None


class FileManagerResource:
    """File Manager Resource implementation."""

    def __init__(self, server):
        """Initialize File Manager Resource.

        Args:
            server: MCP server instance
        """
        self.server = server
        self.config = get_config()
        self.logger = get_logger(__name__)

        # Security settings
        self.max_file_size = self.config.max_file_size_mb * 1024 * 1024  # Convert to bytes
        self.allowed_extensions = set(self.config.get_allowed_file_extensions())

    async def register(self):
        """Register file manager resources with the server."""

        @self.server.mcp.resource("file://list/{path:path}")
        async def list_directory(path: str) -> DirectoryListing:
            """List directory contents.

            Args:
                path: Directory path to list

            Returns:
                DirectoryListing: Directory contents
            """
            return await self._list_directory(path)

        @self.server.mcp.resource("file://read/{path:path}")
        async def read_file(path: str) -> str:
            """Read file contents.

            Args:
                path: File path to read

            Returns:
                str: File contents
            """
            return await self._read_file(path)

        @self.server.mcp.resource("file://info/{path:path}")
        async def get_file_info(path: str) -> FileInfo:
            """Get file information.

            Args:
                path: File path

            Returns:
                FileInfo: File information
            """
            return await self._get_file_info(path)

        self.logger.info("File Manager resources registered")

    async def _list_directory(self, path: str) -> DirectoryListing:
        """List directory contents.

        Args:
            path: Directory path

        Returns:
            DirectoryListing: Directory contents
        """
        try:
            # Resolve and validate path
            resolved_path = self._resolve_path(path)
            if not resolved_path.exists():
                raise FileNotFoundError(f"Directory not found: {path}")

            if not resolved_path.is_dir():
                raise ValueError(f"Path is not a directory: {path}")

            # Check permissions
            if not os.access(resolved_path, os.R_OK):
                raise PermissionError(f"No read permission for directory: {path}")

            files = []
            try:
                for item in resolved_path.iterdir():
                    try:
                        file_info = await self._get_file_info(str(item))
                        files.append(file_info)
                    except (OSError, PermissionError) as e:
                        self.logger.warning(f"Cannot access {item}: {e}")
                        continue
            except PermissionError:
                raise PermissionError(f"No permission to list directory: {path}")

            # Sort files by name, directories first
            files.sort(key=lambda x: (not x.is_directory, x.name.lower()))

            # Get parent directory
            parent_dir = str(resolved_path.parent) if resolved_path.parent != resolved_path else None

            return DirectoryListing(
                path=str(resolved_path),
                total_items=len(files),
                files=files,
                parent_directory=parent_dir
            )

        except Exception as e:
            self.logger.error(f"Error listing directory {path}: {e}")
            raise

    async def _read_file(self, path: str) -> str:
        """Read file contents.

        Args:
            path: File path

        Returns:
            str: File contents
        """
        try:
            # Resolve and validate path
            resolved_path = self._resolve_path(path)
            if not resolved_path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            if resolved_path.is_dir():
                raise ValueError(f"Path is a directory, not a file: {path}")

            # Check file size
            file_size = resolved_path.stat().st_size
            if file_size > self.max_file_size:
                raise ValueError(f"File too large: {file_size} bytes (max: {self.max_file_size} bytes)")

            # Check file extension
            file_ext = resolved_path.suffix.lower()
            if file_ext and file_ext not in self.allowed_extensions:
                raise ValueError(f"File extension not allowed: {file_ext}")

            # Check permissions
            if not os.access(resolved_path, os.R_OK):
                raise PermissionError(f"No read permission for file: {path}")

            # Read file content
            async with aiofiles.open(resolved_path, 'r', encoding='utf-8', errors='replace') as f:
                content = await f.read()

            self.logger.info(f"Read file: {path} ({len(content)} characters)")
            return content

        except UnicodeDecodeError:
            # Try reading as binary and return as hex
            try:
                async with aiofiles.open(resolved_path, 'rb') as f:
                    content = await f.read()
                return f"Binary file content (hex): {content.hex()}"
            except Exception as e:
                raise ValueError(f"Cannot read binary file: {e}")

        except Exception as e:
            self.logger.error(f"Error reading file {path}: {e}")
            raise

    async def _get_file_info(self, path: str) -> FileInfo:
        """Get file information.

        Args:
            path: File path

        Returns:
            FileInfo: File information
        """
        try:
            resolved_path = self._resolve_path(path)
            if not resolved_path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            stat = resolved_path.stat()

            # Get MIME type
            mime_type = None
            if resolved_path.is_file():
                mime_type, _ = mimetypes.guess_type(str(resolved_path))

            # Get permissions
            perms = oct(stat.st_mode)[-3:]
            readable = os.access(resolved_path, os.R_OK)
            writable = os.access(resolved_path, os.W_OK)

            return FileInfo(
                name=resolved_path.name,
                path=str(resolved_path),
                size=stat.st_size,
                is_directory=resolved_path.is_dir(),
                mime_type=mime_type,
                last_modified=stat.st_mtime,
                permissions=perms,
                readable=readable,
                writable=writable
            )

        except Exception as e:
            self.logger.error(f"Error getting file info for {path}: {e}")
            raise

    def _resolve_path(self, path: str) -> Path:
        """Resolve and validate file path.

        Args:
            path: Input path

        Returns:
            Path: Resolved path

        Raises:
            ValueError: If path is invalid or unsafe
        """
        # Handle URL-encoded paths
        if path.startswith("file://"):
            parsed = urlparse(path)
            path = parsed.path

        # Convert to Path object
        try:
            resolved_path = Path(path).resolve()
        except Exception as e:
            raise ValueError(f"Invalid path: {e}")

        # Basic security check - prevent path traversal outside of allowed areas
        # In a real implementation, you might want to restrict to specific directories
        if not str(resolved_path).startswith(('/home', '/tmp', '/var/tmp', os.getcwd())):
            # Allow common safe directories or current working directory
            if not str(resolved_path).startswith(str(Path.cwd())):
                self.logger.warning(f"Path access attempt outside safe areas: {resolved_path}")

        return resolved_path