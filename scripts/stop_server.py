#!/usr/bin/env python3
"""Stop MCP Learning Server script."""

import argparse
import os
import signal
import sys
import time
from pathlib import Path

import psutil
import requests


def find_server_processes():
    """Find running MCP server processes.

    Returns:
        List[psutil.Process]: List of server processes
    """
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and any('start_server.py' in arg for arg in cmdline):
                processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes


def stop_http_server(host: str = "localhost", port: int = 8000, timeout: int = 5):
    """Try to stop HTTP server gracefully via shutdown endpoint.

    Args:
        host: Server host
        port: Server port
        timeout: Request timeout

    Returns:
        bool: True if shutdown was successful
    """
    try:
        response = requests.post(
            f"http://{host}:{port}/shutdown",
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            print(f"✅ HTTP server on {host}:{port} shutdown successfully")
            return True
        else:
            print(f"⚠️  HTTP server responded with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to contact HTTP server: {e}")
        return False


def stop_process_by_pid(pid: int, timeout: int = 10):
    """Stop process by PID gracefully.

    Args:
        pid: Process ID
        timeout: Timeout for graceful shutdown

    Returns:
        bool: True if process was stopped
    """
    try:
        process = psutil.Process(pid)
        print(f"🛑 Stopping process {pid}: {' '.join(process.cmdline())}")

        # Send SIGTERM for graceful shutdown
        process.terminate()

        # Wait for graceful shutdown
        try:
            process.wait(timeout=timeout)
            print(f"✅ Process {pid} stopped gracefully")
            return True
        except psutil.TimeoutExpired:
            print(f"⚠️  Process {pid} didn't stop gracefully, forcing...")
            # Force kill if graceful shutdown failed
            process.kill()
            process.wait(timeout=5)
            print(f"🔥 Process {pid} force killed")
            return True

    except psutil.NoSuchProcess:
        print(f"ℹ️  Process {pid} already stopped")
        return True
    except psutil.AccessDenied:
        print(f"❌ Access denied when stopping process {pid}")
        return False
    except Exception as e:
        print(f"❌ Error stopping process {pid}: {e}")
        return False


def read_pid_file(pid_file: Path):
    """Read PID from file.

    Args:
        pid_file: Path to PID file

    Returns:
        int: PID if found, None otherwise
    """
    try:
        if pid_file.exists():
            pid = int(pid_file.read_text().strip())
            return pid
    except (ValueError, OSError) as e:
        print(f"⚠️  Error reading PID file {pid_file}: {e}")
    return None


def remove_pid_file(pid_file: Path):
    """Remove PID file.

    Args:
        pid_file: Path to PID file
    """
    try:
        if pid_file.exists():
            pid_file.unlink()
            print(f"🗑️  Removed PID file: {pid_file}")
    except OSError as e:
        print(f"⚠️  Error removing PID file {pid_file}: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Stop MCP Learning Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python stop_server.py                          # Stop all server processes
  python stop_server.py --pid 1234              # Stop specific process
  python stop_server.py --http-port 8080        # Try HTTP shutdown first
  python stop_server.py --force                 # Force kill all processes
        """
    )

    parser.add_argument(
        "--pid",
        type=int,
        help="Stop specific process by PID"
    )

    parser.add_argument(
        "--http-host",
        default="localhost",
        help="HTTP server host (for graceful shutdown)"
    )

    parser.add_argument(
        "--http-port",
        type=int,
        default=8000,
        help="HTTP server port (for graceful shutdown)"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force kill processes without graceful shutdown"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout for graceful shutdown (seconds)"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Stop all MCP server processes"
    )

    args = parser.parse_args()

    print("🛑 MCP Learning Server - Stop Script")
    print("=" * 50)

    stopped_any = False

    # Stop specific PID
    if args.pid:
        if stop_process_by_pid(args.pid, args.timeout):
            stopped_any = True
        return 0 if stopped_any else 1

    # Try HTTP graceful shutdown first (unless force mode)
    if not args.force:
        if stop_http_server(args.http_host, args.http_port):
            stopped_any = True
            # Wait a bit for process to actually stop
            time.sleep(2)

    # Find and stop all server processes
    processes = find_server_processes()

    if not processes:
        if not stopped_any:
            print("ℹ️  No MCP server processes found")
        return 0

    print(f"🔍 Found {len(processes)} server process(es)")

    for proc in processes:
        try:
            if args.force:
                print(f"🔥 Force killing process {proc.pid}")
                proc.kill()
                proc.wait(timeout=5)
                print(f"✅ Process {proc.pid} killed")
            else:
                if stop_process_by_pid(proc.pid, args.timeout):
                    stopped_any = True
        except Exception as e:
            print(f"❌ Error handling process {proc.pid}: {e}")

    # Clean up PID files
    pid_files = [
        Path("mcp_server.pid"),
        Path("mcp_http_server.pid"),
        Path("mcp_stdio_server.pid"),
    ]

    for pid_file in pid_files:
        remove_pid_file(pid_file)

    if stopped_any:
        print("✅ Server stop completed")
        return 0
    else:
        print("❌ Failed to stop server")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n🛑 Stop script interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)