"""System Info Resource for MCP Learning Server."""

import os
import platform
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil
from pydantic import BaseModel

from ..utils.config import get_config
from ..utils.logger import get_logger


class SystemInfo(BaseModel):
    """System information model."""
    platform: str
    platform_version: str
    architecture: str
    hostname: str
    username: str
    python_version: str
    python_executable: str
    working_directory: str
    environment_variables: Dict[str, str]


class MemoryInfo(BaseModel):
    """Memory information model."""
    total: int
    available: int
    used: int
    percentage: float
    free: int
    buffers: Optional[int] = None
    cached: Optional[int] = None


class CPUInfo(BaseModel):
    """CPU information model."""
    physical_cores: int
    logical_cores: int
    current_frequency: Optional[float] = None
    min_frequency: Optional[float] = None
    max_frequency: Optional[float] = None
    usage_percentage: float
    usage_per_cpu: List[float]


class DiskInfo(BaseModel):
    """Disk information model."""
    device: str
    mountpoint: str
    filesystem: str
    total: int
    used: int
    free: int
    percentage: float


class NetworkInfo(BaseModel):
    """Network interface information model."""
    interface: str
    addresses: List[str]
    is_up: bool
    speed: Optional[int] = None
    mtu: Optional[int] = None


class ProcessInfo(BaseModel):
    """Process information model."""
    pid: int
    name: str
    username: str
    status: str
    cpu_percent: float
    memory_percent: float
    memory_info: Dict[str, int]
    create_time: float
    cmdline: List[str]


class SystemInfoResource:
    """System Info Resource implementation."""

    def __init__(self, server):
        """Initialize System Info Resource.

        Args:
            server: MCP server instance
        """
        self.server = server
        self.config = get_config()
        self.logger = get_logger(__name__)

    async def register(self):
        """Register system info resources with the server."""

        @self.server.mcp.resource("system://info")
        async def get_system_info() -> SystemInfo:
            """Get system information.

            Returns:
                SystemInfo: System information
            """
            return await self._get_system_info()

        @self.server.mcp.resource("system://memory")
        async def get_memory_info() -> MemoryInfo:
            """Get memory information.

            Returns:
                MemoryInfo: Memory information
            """
            return await self._get_memory_info()

        @self.server.mcp.resource("system://cpu")
        async def get_cpu_info() -> CPUInfo:
            """Get CPU information.

            Returns:
                CPUInfo: CPU information
            """
            return await self._get_cpu_info()

        @self.server.mcp.resource("system://disks")
        async def get_disk_info() -> List[DiskInfo]:
            """Get disk information.

            Returns:
                List[DiskInfo]: Disk information for all mounted disks
            """
            return await self._get_disk_info()

        @self.server.mcp.resource("system://network")
        async def get_network_info() -> List[NetworkInfo]:
            """Get network interface information.

            Returns:
                List[NetworkInfo]: Network interface information
            """
            return await self._get_network_info()

        @self.server.mcp.resource("system://processes")
        async def get_process_list() -> List[ProcessInfo]:
            """Get list of running processes.

            Returns:
                List[ProcessInfo]: List of running processes
            """
            return await self._get_process_list()

        @self.server.mcp.resource("system://uptime")
        async def get_uptime() -> Dict[str, Any]:
            """Get system uptime information.

            Returns:
                Dict[str, Any]: Uptime information
            """
            return await self._get_uptime()

        self.logger.info("System Info resources registered")

    async def _get_system_info(self) -> SystemInfo:
        """Get basic system information.

        Returns:
            SystemInfo: System information
        """
        try:
            # Filter sensitive environment variables
            safe_env_vars = {
                k: v for k, v in os.environ.items()
                if not any(sensitive in k.upper() for sensitive in [
                    'PASSWORD', 'SECRET', 'KEY', 'TOKEN', 'CREDENTIAL'
                ])
            }

            return SystemInfo(
                platform=platform.system(),
                platform_version=platform.version(),
                architecture=platform.machine(),
                hostname=platform.node(),
                username=os.getlogin() if hasattr(os, 'getlogin') else os.environ.get('USER', 'unknown'),
                python_version=sys.version,
                python_executable=sys.executable,
                working_directory=os.getcwd(),
                environment_variables=safe_env_vars
            )

        except Exception as e:
            self.logger.error(f"Error getting system info: {e}")
            raise

    async def _get_memory_info(self) -> MemoryInfo:
        """Get memory information.

        Returns:
            MemoryInfo: Memory information
        """
        try:
            memory = psutil.virtual_memory()

            memory_info = MemoryInfo(
                total=memory.total,
                available=memory.available,
                used=memory.used,
                percentage=memory.percent,
                free=memory.free
            )

            # Add platform-specific fields if available
            if hasattr(memory, 'buffers'):
                memory_info.buffers = memory.buffers
            if hasattr(memory, 'cached'):
                memory_info.cached = memory.cached

            return memory_info

        except Exception as e:
            self.logger.error(f"Error getting memory info: {e}")
            raise

    async def _get_cpu_info(self) -> CPUInfo:
        """Get CPU information.

        Returns:
            CPUInfo: CPU information
        """
        try:
            # Get CPU frequency (may not be available on all systems)
            cpu_freq = None
            min_freq = None
            max_freq = None
            try:
                freq_info = psutil.cpu_freq()
                if freq_info:
                    cpu_freq = freq_info.current
                    min_freq = freq_info.min
                    max_freq = freq_info.max
            except Exception:
                pass

            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_percent_per_cpu = psutil.cpu_percent(interval=1, percpu=True)

            return CPUInfo(
                physical_cores=psutil.cpu_count(logical=False) or 0,
                logical_cores=psutil.cpu_count(logical=True) or 0,
                current_frequency=cpu_freq,
                min_frequency=min_freq,
                max_frequency=max_freq,
                usage_percentage=cpu_percent,
                usage_per_cpu=cpu_percent_per_cpu
            )

        except Exception as e:
            self.logger.error(f"Error getting CPU info: {e}")
            raise

    async def _get_disk_info(self) -> List[DiskInfo]:
        """Get disk information.

        Returns:
            List[DiskInfo]: List of disk information
        """
        try:
            disks = []
            partitions = psutil.disk_partitions()

            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disks.append(DiskInfo(
                        device=partition.device,
                        mountpoint=partition.mountpoint,
                        filesystem=partition.fstype,
                        total=usage.total,
                        used=usage.used,
                        free=usage.free,
                        percentage=(usage.used / usage.total * 100) if usage.total > 0 else 0
                    ))
                except PermissionError:
                    # Skip partitions we can't access
                    continue
                except Exception as e:
                    self.logger.warning(f"Error getting disk info for {partition.device}: {e}")
                    continue

            return disks

        except Exception as e:
            self.logger.error(f"Error getting disk info: {e}")
            raise

    async def _get_network_info(self) -> List[NetworkInfo]:
        """Get network interface information.

        Returns:
            List[NetworkInfo]: List of network interfaces
        """
        try:
            interfaces = []
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()

            for interface_name, addresses in net_if_addrs.items():
                # Get IP addresses
                ip_addresses = []
                for addr in addresses:
                    if addr.family.name in ['AF_INET', 'AF_INET6']:
                        ip_addresses.append(addr.address)

                # Get interface stats
                stats = net_if_stats.get(interface_name)
                is_up = stats.isup if stats else False
                speed = stats.speed if stats else None
                mtu = stats.mtu if stats else None

                interfaces.append(NetworkInfo(
                    interface=interface_name,
                    addresses=ip_addresses,
                    is_up=is_up,
                    speed=speed,
                    mtu=mtu
                ))

            return interfaces

        except Exception as e:
            self.logger.error(f"Error getting network info: {e}")
            raise

    async def _get_process_list(self) -> List[ProcessInfo]:
        """Get list of running processes.

        Returns:
            List[ProcessInfo]: List of processes (limited to top 50 by CPU usage)
        """
        try:
            processes = []

            # Get all processes and sort by CPU usage
            all_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'status', 'cpu_percent', 'memory_percent', 'memory_info', 'create_time', 'cmdline']):
                try:
                    proc_info = proc.info
                    all_processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort by CPU usage and take top 50
            all_processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            top_processes = all_processes[:50]

            for proc_info in top_processes:
                try:
                    processes.append(ProcessInfo(
                        pid=proc_info['pid'],
                        name=proc_info['name'] or 'unknown',
                        username=proc_info['username'] or 'unknown',
                        status=proc_info['status'] or 'unknown',
                        cpu_percent=proc_info['cpu_percent'] or 0.0,
                        memory_percent=proc_info['memory_percent'] or 0.0,
                        memory_info=proc_info['memory_info']._asdict() if proc_info['memory_info'] else {},
                        create_time=proc_info['create_time'] or 0.0,
                        cmdline=proc_info['cmdline'] or []
                    ))
                except Exception as e:
                    self.logger.warning(f"Error processing process info: {e}")
                    continue

            return processes

        except Exception as e:
            self.logger.error(f"Error getting process list: {e}")
            raise

    async def _get_uptime(self) -> Dict[str, Any]:
        """Get system uptime information.

        Returns:
            Dict[str, Any]: Uptime information
        """
        try:
            boot_time = psutil.boot_time()
            current_time = datetime.now().timestamp()
            uptime_seconds = current_time - boot_time

            return {
                "boot_time": datetime.fromtimestamp(boot_time).isoformat(),
                "current_time": datetime.fromtimestamp(current_time).isoformat(),
                "uptime_seconds": uptime_seconds,
                "uptime_days": uptime_seconds // 86400,
                "uptime_hours": (uptime_seconds % 86400) // 3600,
                "uptime_minutes": (uptime_seconds % 3600) // 60
            }

        except Exception as e:
            self.logger.error(f"Error getting uptime: {e}")
            raise