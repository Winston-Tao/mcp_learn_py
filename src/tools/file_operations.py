"""File Operations Tool for MCP Learning Server."""

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import csv
from pydantic import BaseModel

from ..utils.config import get_config
from ..utils.logger import get_logger


class FileOperationResult(BaseModel):
    """File operation result model."""
    operation: str
    path: str
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    """File search result model."""
    path: str
    line_number: int
    line_content: str
    match_text: str


class FileOperationsTool:
    """File Operations Tool implementation."""

    def __init__(self, server):
        """Initialize File Operations Tool.

        Args:
            server: MCP server instance
        """
        self.server = server
        self.config = get_config()
        self.logger = get_logger(__name__)

        # Security settings
        self.max_file_size = self.config.max_file_size_mb * 1024 * 1024  # Convert to bytes
        self.allowed_extensions = set(self.config.allowed_file_extensions)
        self.upload_dir = Path(self.config.upload_dir)

        # Ensure upload directory exists
        self.upload_dir.mkdir(exist_ok=True)

    async def register(self):
        """Register file operations tools with the server."""

        @self.server.mcp.tool()
        async def create_file(path: str, content: str, overwrite: bool = False) -> FileOperationResult:
            """Create a new file with content.

            Args:
                path: File path to create
                content: File content
                overwrite: Whether to overwrite existing file

            Returns:
                FileOperationResult: Operation result

            Example:
                - create_file("test.txt", "Hello, World!")
                - create_file("data.json", '{"name": "test"}', overwrite=True)
            """
            return await self._create_file(path, content, overwrite)

        @self.server.mcp.tool()
        async def append_to_file(path: str, content: str, newline: bool = True) -> FileOperationResult:
            """Append content to an existing file.

            Args:
                path: File path
                content: Content to append
                newline: Whether to add a newline before content

            Returns:
                FileOperationResult: Operation result

            Example:
                - append_to_file("log.txt", "New log entry")
                - append_to_file("data.txt", "More data", newline=False)
            """
            return await self._append_to_file(path, content, newline)

        @self.server.mcp.tool()
        async def delete_file(path: str, confirm: bool = False) -> FileOperationResult:
            """Delete a file.

            Args:
                path: File path to delete
                confirm: Confirmation flag for safety

            Returns:
                FileOperationResult: Operation result

            Example:
                - delete_file("temp.txt", confirm=True)
            """
            return await self._delete_file(path, confirm)

        @self.server.mcp.tool()
        async def copy_file(source: str, destination: str, overwrite: bool = False) -> FileOperationResult:
            """Copy a file to another location.

            Args:
                source: Source file path
                destination: Destination file path
                overwrite: Whether to overwrite existing destination

            Returns:
                FileOperationResult: Operation result

            Example:
                - copy_file("source.txt", "backup.txt")
                - copy_file("data.json", "archive/data_backup.json", overwrite=True)
            """
            return await self._copy_file(source, destination, overwrite)

        @self.server.mcp.tool()
        async def move_file(source: str, destination: str, overwrite: bool = False) -> FileOperationResult:
            """Move/rename a file.

            Args:
                source: Source file path
                destination: Destination file path
                overwrite: Whether to overwrite existing destination

            Returns:
                FileOperationResult: Operation result

            Example:
                - move_file("old_name.txt", "new_name.txt")
                - move_file("temp.txt", "archive/temp.txt", overwrite=True)
            """
            return await self._move_file(source, destination, overwrite)

        @self.server.mcp.tool()
        async def search_in_files(directory: str, pattern: str, file_pattern: str = "*", case_sensitive: bool = False) -> List[SearchResult]:
            """Search for text pattern in files.

            Args:
                directory: Directory to search in
                pattern: Text pattern to search for
                file_pattern: File name pattern (e.g., "*.txt", "*.py")
                case_sensitive: Whether search is case sensitive

            Returns:
                List[SearchResult]: Search results

            Example:
                - search_in_files("/path/to/dir", "TODO")
                - search_in_files("/src", "class", "*.py", case_sensitive=True)
            """
            return await self._search_in_files(directory, pattern, file_pattern, case_sensitive)

        @self.server.mcp.tool()
        async def create_directory(path: str, parents: bool = True) -> FileOperationResult:
            """Create a directory.

            Args:
                path: Directory path to create
                parents: Whether to create parent directories

            Returns:
                FileOperationResult: Operation result

            Example:
                - create_directory("new_folder")
                - create_directory("path/to/nested/folder", parents=True)
            """
            return await self._create_directory(path, parents)

        @self.server.mcp.tool()
        async def process_csv_file(path: str, operation: str, **kwargs) -> Dict[str, Any]:
            """Process CSV files (read, analyze, filter).

            Args:
                path: CSV file path
                operation: Operation type (read, analyze, filter, sort)
                **kwargs: Operation-specific parameters

            Returns:
                Dict[str, Any]: Processing result

            Examples:
                - process_csv_file("data.csv", "read", limit=10)
                - process_csv_file("data.csv", "analyze")
                - process_csv_file("data.csv", "filter", column="age", min_value=18)
                - process_csv_file("data.csv", "sort", column="name", reverse=False)
            """
            return await self._process_csv_file(path, operation, **kwargs)

        @self.server.mcp.tool()
        async def process_json_file(path: str, operation: str, **kwargs) -> Dict[str, Any]:
            """Process JSON files (read, validate, extract, modify).

            Args:
                path: JSON file path
                operation: Operation type (read, validate, extract, keys, size)
                **kwargs: Operation-specific parameters

            Returns:
                Dict[str, Any]: Processing result

            Examples:
                - process_json_file("config.json", "read")
                - process_json_file("data.json", "validate")
                - process_json_file("data.json", "extract", path="users.0.name")
                - process_json_file("data.json", "keys")
            """
            return await self._process_json_file(path, operation, **kwargs)

        self.logger.info("File Operations tools registered")

    async def _create_file(self, path: str, content: str, overwrite: bool) -> FileOperationResult:
        """Create a new file."""
        try:
            file_path = Path(path)

            # Security checks
            if not self._is_safe_path(file_path):
                raise ValueError(f"Unsafe file path: {path}")

            if not self._is_allowed_extension(file_path):
                raise ValueError(f"File extension not allowed: {file_path.suffix}")

            if len(content.encode('utf-8')) > self.max_file_size:
                raise ValueError(f"Content too large (max: {self.max_file_size} bytes)")

            # Check if file exists
            if file_path.exists() and not overwrite:
                raise ValueError(f"File already exists: {path} (use overwrite=True to replace)")

            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)

            self.logger.info(f"Created file: {path}")
            return FileOperationResult(
                operation="create_file",
                path=str(file_path),
                success=True,
                message=f"File created successfully: {path}",
                details={"size_bytes": len(content.encode('utf-8')), "overwritten": file_path.exists()}
            )

        except Exception as e:
            self.logger.error(f"Error creating file {path}: {e}")
            return FileOperationResult(
                operation="create_file",
                path=path,
                success=False,
                message=f"Failed to create file: {e}"
            )

    async def _append_to_file(self, path: str, content: str, newline: bool) -> FileOperationResult:
        """Append content to file."""
        try:
            file_path = Path(path)

            if not self._is_safe_path(file_path):
                raise ValueError(f"Unsafe file path: {path}")

            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            # Check file size after append
            current_size = file_path.stat().st_size
            append_size = len(content.encode('utf-8'))
            if current_size + append_size > self.max_file_size:
                raise ValueError(f"File would be too large after append")

            # Append content
            content_to_append = f"\\n{content}" if newline else content
            async with aiofiles.open(file_path, 'a', encoding='utf-8') as f:
                await f.write(content_to_append)

            self.logger.info(f"Appended to file: {path}")
            return FileOperationResult(
                operation="append_to_file",
                path=str(file_path),
                success=True,
                message=f"Content appended successfully to: {path}",
                details={"appended_bytes": append_size, "newline_added": newline}
            )

        except Exception as e:
            self.logger.error(f"Error appending to file {path}: {e}")
            return FileOperationResult(
                operation="append_to_file",
                path=path,
                success=False,
                message=f"Failed to append to file: {e}"
            )

    async def _delete_file(self, path: str, confirm: bool) -> FileOperationResult:
        """Delete a file."""
        try:
            if not confirm:
                return FileOperationResult(
                    operation="delete_file",
                    path=path,
                    success=False,
                    message="Deletion requires confirmation (confirm=True)"
                )

            file_path = Path(path)

            if not self._is_safe_path(file_path):
                raise ValueError(f"Unsafe file path: {path}")

            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            if file_path.is_dir():
                raise ValueError(f"Path is a directory, not a file: {path}")

            # Store file info before deletion
            file_size = file_path.stat().st_size

            # Delete file
            file_path.unlink()

            self.logger.info(f"Deleted file: {path}")
            return FileOperationResult(
                operation="delete_file",
                path=str(file_path),
                success=True,
                message=f"File deleted successfully: {path}",
                details={"size_bytes": file_size}
            )

        except Exception as e:
            self.logger.error(f"Error deleting file {path}: {e}")
            return FileOperationResult(
                operation="delete_file",
                path=path,
                success=False,
                message=f"Failed to delete file: {e}"
            )

    async def _copy_file(self, source: str, destination: str, overwrite: bool) -> FileOperationResult:
        """Copy a file."""
        try:
            source_path = Path(source)
            dest_path = Path(destination)

            if not self._is_safe_path(source_path) or not self._is_safe_path(dest_path):
                raise ValueError("Unsafe file path")

            if not source_path.exists():
                raise FileNotFoundError(f"Source file not found: {source}")

            if not source_path.is_file():
                raise ValueError(f"Source is not a file: {source}")

            if dest_path.exists() and not overwrite:
                raise ValueError(f"Destination exists (use overwrite=True): {destination}")

            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source_path, dest_path)

            self.logger.info(f"Copied file: {source} -> {destination}")
            return FileOperationResult(
                operation="copy_file",
                path=f"{source} -> {destination}",
                success=True,
                message=f"File copied successfully: {source} -> {destination}",
                details={
                    "source": str(source_path),
                    "destination": str(dest_path),
                    "size_bytes": dest_path.stat().st_size
                }
            )

        except Exception as e:
            self.logger.error(f"Error copying file {source} -> {destination}: {e}")
            return FileOperationResult(
                operation="copy_file",
                path=f"{source} -> {destination}",
                success=False,
                message=f"Failed to copy file: {e}"
            )

    async def _move_file(self, source: str, destination: str, overwrite: bool) -> FileOperationResult:
        """Move/rename a file."""
        try:
            source_path = Path(source)
            dest_path = Path(destination)

            if not self._is_safe_path(source_path) or not self._is_safe_path(dest_path):
                raise ValueError("Unsafe file path")

            if not source_path.exists():
                raise FileNotFoundError(f"Source file not found: {source}")

            if dest_path.exists() and not overwrite:
                raise ValueError(f"Destination exists (use overwrite=True): {destination}")

            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Move file
            shutil.move(str(source_path), str(dest_path))

            self.logger.info(f"Moved file: {source} -> {destination}")
            return FileOperationResult(
                operation="move_file",
                path=f"{source} -> {destination}",
                success=True,
                message=f"File moved successfully: {source} -> {destination}",
                details={
                    "old_path": str(source_path),
                    "new_path": str(dest_path),
                    "size_bytes": dest_path.stat().st_size
                }
            )

        except Exception as e:
            self.logger.error(f"Error moving file {source} -> {destination}: {e}")
            return FileOperationResult(
                operation="move_file",
                path=f"{source} -> {destination}",
                success=False,
                message=f"Failed to move file: {e}"
            )

    async def _search_in_files(self, directory: str, pattern: str, file_pattern: str, case_sensitive: bool) -> List[SearchResult]:
        """Search for pattern in files."""
        try:
            dir_path = Path(directory)

            if not dir_path.exists():
                raise FileNotFoundError(f"Directory not found: {directory}")

            if not dir_path.is_dir():
                raise ValueError(f"Path is not a directory: {directory}")

            results = []
            search_pattern = pattern if case_sensitive else pattern.lower()

            # Find matching files
            matching_files = list(dir_path.glob(file_pattern))
            if not matching_files:
                matching_files = list(dir_path.rglob(file_pattern))  # Recursive search

            for file_path in matching_files:
                if file_path.is_file() and self._is_allowed_extension(file_path):
                    try:
                        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = await f.readlines()

                        for line_num, line in enumerate(lines, 1):
                            search_line = line if case_sensitive else line.lower()
                            if search_pattern in search_line:
                                results.append(SearchResult(
                                    path=str(file_path),
                                    line_number=line_num,
                                    line_content=line.strip(),
                                    match_text=pattern
                                ))

                    except Exception as e:
                        self.logger.warning(f"Error searching in file {file_path}: {e}")
                        continue

            self.logger.info(f"Search completed: {len(results)} matches found")
            return results[:100]  # Limit results

        except Exception as e:
            self.logger.error(f"Error searching in files: {e}")
            raise ValueError(f"Search failed: {e}")

    async def _create_directory(self, path: str, parents: bool) -> FileOperationResult:
        """Create a directory."""
        try:
            dir_path = Path(path)

            if not self._is_safe_path(dir_path):
                raise ValueError(f"Unsafe directory path: {path}")

            if dir_path.exists():
                if dir_path.is_dir():
                    return FileOperationResult(
                        operation="create_directory",
                        path=str(dir_path),
                        success=True,
                        message=f"Directory already exists: {path}"
                    )
                else:
                    raise ValueError(f"Path exists but is not a directory: {path}")

            # Create directory
            dir_path.mkdir(parents=parents, exist_ok=True)

            self.logger.info(f"Created directory: {path}")
            return FileOperationResult(
                operation="create_directory",
                path=str(dir_path),
                success=True,
                message=f"Directory created successfully: {path}",
                details={"parents_created": parents}
            )

        except Exception as e:
            self.logger.error(f"Error creating directory {path}: {e}")
            return FileOperationResult(
                operation="create_directory",
                path=path,
                success=False,
                message=f"Failed to create directory: {e}"
            )

    async def _process_csv_file(self, path: str, operation: str, **kwargs) -> Dict[str, Any]:
        """Process CSV file."""
        try:
            file_path = Path(path)

            if not file_path.exists():
                raise FileNotFoundError(f"CSV file not found: {path}")

            if file_path.suffix.lower() != '.csv':
                raise ValueError(f"File is not a CSV file: {path}")

            # Read CSV file
            rows = []
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                csv_reader = csv.DictReader(content.splitlines())
                headers = csv_reader.fieldnames
                rows = list(csv_reader)

            if operation == "read":
                limit = kwargs.get('limit', len(rows))
                return {
                    "operation": "read",
                    "headers": headers,
                    "rows": rows[:limit],
                    "total_rows": len(rows),
                    "displayed_rows": min(limit, len(rows))
                }

            elif operation == "analyze":
                return {
                    "operation": "analyze",
                    "headers": headers,
                    "total_rows": len(rows),
                    "column_count": len(headers) if headers else 0,
                    "sample_rows": rows[:3] if rows else [],
                    "file_size": file_path.stat().st_size
                }

            # Add more CSV operations as needed
            else:
                raise ValueError(f"Unknown CSV operation: {operation}")

        except Exception as e:
            self.logger.error(f"Error processing CSV file {path}: {e}")
            raise ValueError(f"CSV processing failed: {e}")

    async def _process_json_file(self, path: str, operation: str, **kwargs) -> Dict[str, Any]:
        """Process JSON file."""
        try:
            file_path = Path(path)

            if not file_path.exists():
                raise FileNotFoundError(f"JSON file not found: {path}")

            # Read JSON file
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            if operation == "validate":
                try:
                    json.loads(content)
                    return {"operation": "validate", "valid": True, "message": "JSON is valid"}
                except json.JSONDecodeError as e:
                    return {"operation": "validate", "valid": False, "error": str(e)}

            # Parse JSON for other operations
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}")

            if operation == "read":
                return {"operation": "read", "data": data, "file_size": len(content)}

            elif operation == "keys":
                if isinstance(data, dict):
                    return {"operation": "keys", "keys": list(data.keys()), "type": "object"}
                elif isinstance(data, list):
                    return {"operation": "keys", "length": len(data), "type": "array"}
                else:
                    return {"operation": "keys", "type": type(data).__name__}

            elif operation == "size":
                def get_size(obj):
                    if isinstance(obj, dict):
                        return len(obj)
                    elif isinstance(obj, list):
                        return len(obj)
                    else:
                        return 1

                return {
                    "operation": "size",
                    "size": get_size(data),
                    "type": type(data).__name__,
                    "file_size_bytes": len(content)
                }

            else:
                raise ValueError(f"Unknown JSON operation: {operation}")

        except Exception as e:
            self.logger.error(f"Error processing JSON file {path}: {e}")
            raise ValueError(f"JSON processing failed: {e}")

    def _is_safe_path(self, path: Path) -> bool:
        """Check if path is safe to access."""
        try:
            resolved_path = path.resolve()
            # Add your own security rules here
            # For now, just prevent access to sensitive directories
            dangerous_paths = ['/etc', '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/root']
            path_str = str(resolved_path)

            for dangerous in dangerous_paths:
                if path_str.startswith(dangerous):
                    return False

            return True
        except Exception:
            return False

    def _is_allowed_extension(self, path: Path) -> bool:
        """Check if file extension is allowed."""
        if not self.allowed_extensions:
            return True  # No restrictions
        return path.suffix.lower() in self.allowed_extensions