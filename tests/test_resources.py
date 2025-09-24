"""Tests for MCP Learning Server resources."""

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

import sys

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.resources.file_manager import FileManagerResource
from src.resources.system_info import SystemInfoResource
from src.server import MCPLearningServer


@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = MagicMock()
    server.mcp = MagicMock()
    return server


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


class TestFileManagerResource:
    """Test cases for File Manager Resource."""

    @pytest.fixture
    def file_manager(self, mock_server):
        """Create a file manager resource instance."""
        return FileManagerResource(mock_server)

    def test_initialization(self, file_manager):
        """Test file manager initialization."""
        assert file_manager.server is not None
        assert file_manager.config is not None
        assert file_manager.logger is not None
        assert file_manager.max_file_size > 0
        assert isinstance(file_manager.allowed_extensions, set)

    @pytest.mark.asyncio
    async def test_get_file_info(self, file_manager, temp_directory):
        """Test getting file information."""
        # Create a test file
        test_file = temp_directory / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)

        # Get file info
        file_info = await file_manager._get_file_info(str(test_file))

        assert file_info.name == "test.txt"
        assert file_info.path == str(test_file)
        assert file_info.size == len(test_content)
        assert not file_info.is_directory
        assert file_info.readable
        assert file_info.writable

    @pytest.mark.asyncio
    async def test_read_file(self, file_manager, temp_directory):
        """Test reading file contents."""
        # Create a test file
        test_file = temp_directory / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)

        # Read file
        content = await file_manager._read_file(str(test_file))
        assert content == test_content

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, file_manager):
        """Test reading a non-existent file."""
        with pytest.raises(FileNotFoundError):
            await file_manager._read_file("/nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_list_directory(self, file_manager, temp_directory):
        """Test listing directory contents."""
        # Create test files and directories
        (temp_directory / "file1.txt").write_text("content1")
        (temp_directory / "file2.txt").write_text("content2")
        (temp_directory / "subdir").mkdir()
        (temp_directory / "subdir" / "file3.txt").write_text("content3")

        # List directory
        listing = await file_manager._list_directory(str(temp_directory))

        assert listing.path == str(temp_directory)
        assert listing.total_items >= 3  # At least file1.txt, file2.txt, subdir

        # Check that files are present
        file_names = [f.name for f in listing.files]
        assert "file1.txt" in file_names
        assert "file2.txt" in file_names
        assert "subdir" in file_names

    @pytest.mark.asyncio
    async def test_list_nonexistent_directory(self, file_manager):
        """Test listing a non-existent directory."""
        with pytest.raises(FileNotFoundError):
            await file_manager._list_directory("/nonexistent/directory")

    def test_resolve_path(self, file_manager, temp_directory):
        """Test path resolution."""
        test_file = temp_directory / "test.txt"
        test_file.write_text("content")

        resolved = file_manager._resolve_path(str(test_file))
        assert resolved == test_file.resolve()

    def test_resolve_relative_path(self, file_manager):
        """Test resolving relative paths."""
        resolved = file_manager._resolve_path("./test.txt")
        assert resolved.is_absolute()

    @pytest.mark.asyncio
    async def test_large_file_rejection(self, file_manager, temp_directory):
        """Test rejection of files that are too large."""
        # Create a file larger than the limit
        test_file = temp_directory / "large.txt"
        # Temporarily set a very small limit for testing
        original_limit = file_manager.max_file_size
        file_manager.max_file_size = 10

        try:
            test_file.write_text("This is definitely more than 10 bytes")

            with pytest.raises(ValueError, match="File too large"):
                await file_manager._read_file(str(test_file))
        finally:
            file_manager.max_file_size = original_limit

    @pytest.mark.asyncio
    async def test_disallowed_extension(self, file_manager, temp_directory):
        """Test handling of disallowed file extensions."""
        # Create a file with disallowed extension
        test_file = temp_directory / "test.exe"
        test_file.write_text("content")

        # Temporarily restrict allowed extensions
        original_extensions = file_manager.allowed_extensions
        file_manager.allowed_extensions = {".txt", ".json"}

        try:
            with pytest.raises(ValueError, match="File extension not allowed"):
                await file_manager._read_file(str(test_file))
        finally:
            file_manager.allowed_extensions = original_extensions


class TestSystemInfoResource:
    """Test cases for System Info Resource."""

    @pytest.fixture
    def system_info(self, mock_server):
        """Create a system info resource instance."""
        return SystemInfoResource(mock_server)

    def test_initialization(self, system_info):
        """Test system info initialization."""
        assert system_info.server is not None
        assert system_info.config is not None
        assert system_info.logger is not None

    @pytest.mark.asyncio
    async def test_get_system_info(self, system_info):
        """Test getting basic system information."""
        info = await system_info._get_system_info()

        assert info.platform is not None
        assert info.platform_version is not None
        assert info.architecture is not None
        assert info.hostname is not None
        assert info.python_version is not None
        assert info.python_executable is not None
        assert info.working_directory is not None
        assert isinstance(info.environment_variables, dict)

        # Check that sensitive variables are filtered out
        for key in info.environment_variables:
            assert not any(sensitive in key.upper() for sensitive in
                          ['PASSWORD', 'SECRET', 'KEY', 'TOKEN', 'CREDENTIAL'])

    @pytest.mark.asyncio
    async def test_get_memory_info(self, system_info):
        """Test getting memory information."""
        with patch('psutil.virtual_memory') as mock_memory:
            # Mock memory info
            mock_memory.return_value = MagicMock(
                total=8589934592,  # 8GB
                available=4294967296,  # 4GB
                used=4294967296,  # 4GB
                percentage=50.0,
                free=4294967296  # 4GB
            )

            memory_info = await system_info._get_memory_info()

            assert memory_info.total == 8589934592
            assert memory_info.available == 4294967296
            assert memory_info.used == 4294967296
            assert memory_info.percentage == 50.0
            assert memory_info.free == 4294967296

    @pytest.mark.asyncio
    async def test_get_cpu_info(self, system_info):
        """Test getting CPU information."""
        with patch('psutil.cpu_count') as mock_count, \\
             patch('psutil.cpu_percent') as mock_percent:

            mock_count.side_effect = lambda logical=True: 8 if logical else 4
            mock_percent.side_effect = lambda interval=None, percpu=False: \\
                [10.0, 20.0, 15.0, 5.0] if percpu else 12.5

            cpu_info = await system_info._get_cpu_info()

            assert cpu_info.physical_cores == 4
            assert cpu_info.logical_cores == 8
            assert cpu_info.usage_percentage == 12.5
            assert len(cpu_info.usage_per_cpu) == 4

    @pytest.mark.asyncio
    async def test_get_disk_info(self, system_info):
        """Test getting disk information."""
        with patch('psutil.disk_partitions') as mock_partitions, \\
             patch('psutil.disk_usage') as mock_usage:

            # Mock partition info
            mock_partition = MagicMock()
            mock_partition.device = "/dev/sda1"
            mock_partition.mountpoint = "/"
            mock_partition.fstype = "ext4"
            mock_partitions.return_value = [mock_partition]

            # Mock usage info
            mock_usage.return_value = MagicMock(
                total=1000000000,  # 1GB
                used=500000000,    # 500MB
                free=500000000     # 500MB
            )

            disk_info = await system_info._get_disk_info()

            assert len(disk_info) == 1
            disk = disk_info[0]
            assert disk.device == "/dev/sda1"
            assert disk.mountpoint == "/"
            assert disk.filesystem == "ext4"
            assert disk.total == 1000000000
            assert disk.used == 500000000
            assert disk.free == 500000000
            assert disk.percentage == 50.0

    @pytest.mark.asyncio
    async def test_get_network_info(self, system_info):
        """Test getting network interface information."""
        with patch('psutil.net_if_addrs') as mock_addrs, \\
             patch('psutil.net_if_stats') as mock_stats:

            # Mock address info
            mock_addr = MagicMock()
            mock_addr.family.name = "AF_INET"
            mock_addr.address = "192.168.1.100"
            mock_addrs.return_value = {"eth0": [mock_addr]}

            # Mock stats info
            mock_stat = MagicMock()
            mock_stat.isup = True
            mock_stat.speed = 1000
            mock_stat.mtu = 1500
            mock_stats.return_value = {"eth0": mock_stat}

            network_info = await system_info._get_network_info()

            assert len(network_info) == 1
            interface = network_info[0]
            assert interface.interface == "eth0"
            assert "192.168.1.100" in interface.addresses
            assert interface.is_up is True
            assert interface.speed == 1000
            assert interface.mtu == 1500

    @pytest.mark.asyncio
    async def test_get_uptime(self, system_info):
        """Test getting system uptime."""
        with patch('psutil.boot_time') as mock_boot, \\
             patch('datetime.datetime') as mock_datetime:

            mock_boot.return_value = 1000000000  # Mock boot time
            mock_datetime.now.return_value.timestamp.return_value = 1000003600  # 1 hour later

            uptime = await system_info._get_uptime()

            assert "boot_time" in uptime
            assert "current_time" in uptime
            assert "uptime_seconds" in uptime
            assert uptime["uptime_seconds"] == 3600  # 1 hour
            assert uptime["uptime_hours"] == 1

    @pytest.mark.asyncio
    async def test_get_process_list(self, system_info):
        """Test getting process list."""
        with patch('psutil.process_iter') as mock_iter:
            # Mock process info
            mock_process = MagicMock()
            mock_process.info = {
                'pid': 1234,
                'name': 'test_process',
                'username': 'testuser',
                'status': 'running',
                'cpu_percent': 10.5,
                'memory_percent': 5.2,
                'memory_info': MagicMock(_asdict=lambda: {'rss': 1024000, 'vms': 2048000}),
                'create_time': 1000000000,
                'cmdline': ['test_process', '--arg1', '--arg2']
            }
            mock_iter.return_value = [mock_process]

            processes = await system_info._get_process_list()

            assert len(processes) >= 1
            process = processes[0]
            assert process.pid == 1234
            assert process.name == 'test_process'
            assert process.username == 'testuser'
            assert process.status == 'running'
            assert process.cpu_percent == 10.5
            assert process.memory_percent == 5.2