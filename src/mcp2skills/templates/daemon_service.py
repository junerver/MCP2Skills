"""MCP Daemon Service template for persistent MCP connections."""

DAEMON_SERVICE_TEMPLATE = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Daemon Service - Persistent MCP server connection with HTTP API.

This daemon maintains a long-lived connection to the MCP server and exposes
an HTTP API for tool invocation. It handles:
- Automatic connection management and reconnection
- Process lifecycle with PID file
- Graceful shutdown
- Health monitoring
"""

import asyncio
import json
import os
import sys
import signal
import time
import logging
from pathlib import Path
from contextlib import AsyncExitStack
from typing import Optional, Any

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    from aiohttp import web
except ImportError:
    print("Error: aiohttp not installed. Run: pip install aiohttp", file=sys.stderr)
    sys.exit(1)

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("Error: mcp package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Configuration
DAEMON_HOST = "127.0.0.1"
DAEMON_PORT = {daemon_port}
DAEMON_TIMEOUT = {daemon_timeout}  # seconds, 0 means no timeout
SKILL_DIR = Path(__file__).parent
CONFIG_PATH = SKILL_DIR / "mcp-config.json"
PID_FILE = SKILL_DIR / ".daemon.pid"
LOG_FILE = SKILL_DIR / "daemon.log"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MCPDaemonService:
    """
    Persistent MCP daemon that maintains long-lived connection to MCP server.

    Features:
    - Automatic reconnection on connection loss
    - Tool caching for faster responses
    - Graceful shutdown handling
    - Health monitoring endpoint
    """

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack: Optional[AsyncExitStack] = None
        self.running = False
        self.connected = False
        self.tools_cache = None
        self.last_error: Optional[str] = None
        self.connection_time: Optional[float] = None
        self.last_activity: Optional[float] = None
        self.reconnect_task: Optional[asyncio.Task] = None
        self.timeout_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def load_config(self) -> dict:
        """Load MCP configuration from mcp-config.json."""
        if not CONFIG_PATH.exists():
            raise RuntimeError(f"Config not found: {CONFIG_PATH}")

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Fix command path for cross-platform compatibility
        command = config.get("command", "")
        if sys.platform != "win32" and command.endswith(".cmd"):
            base_cmd = Path(command).stem
            if base_cmd in ("npx", "node", "npm"):
                config["command"] = base_cmd
        elif sys.platform == "win32" and not command.endswith((".cmd", ".exe", ".bat")):
            if command in ("npx", "node", "npm"):
                import shutil
                found = shutil.which(command)
                if found:
                    config["command"] = found

        return config

    async def connect(self) -> bool:
        """Establish connection to MCP server."""
        async with self._lock:
            if self.connected and self.session:
                return True

            try:
                config = self.load_config()

                server_params = StdioServerParameters(
                    command=config.get("command", ""),
                    args=config.get("args", []),
                    env=config.get("env", {}),
                )

                # Close existing connection if any
                if self.exit_stack:
                    try:
                        await self.exit_stack.aclose()
                    except Exception:
                        pass

                self.exit_stack = AsyncExitStack()

                # Connect to MCP server
                stdio_transport = await self.exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
                read_stream, write_stream = stdio_transport

                self.session = await self.exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )

                await self.session.initialize()

                self.connected = True
                self.connection_time = time.time()
                self.last_activity = time.time()
                self.last_error = None
                self.tools_cache = None  # Clear cache on reconnect

                logger.info("Connected to MCP server successfully")
                return True

            except Exception as e:
                self.connected = False
                self.last_error = str(e)
                logger.error(f"Failed to connect to MCP server: {e}")
                return False

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()

    async def ensure_connected(self) -> bool:
        """Ensure connection is established, reconnect if needed."""
        if not self.connected or not self.session:
            return await self.connect()
        self.update_activity()
        return True

    async def list_tools(self) -> list[dict]:
        """List available tools from MCP server."""
        if not await self.ensure_connected():
            raise RuntimeError(f"Not connected to MCP server: {self.last_error}")

        # Use cached tools if available
        if self.tools_cache is not None:
            return self.tools_cache

        try:
            result = await self.session.list_tools()
            self.tools_cache = [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": tool.inputSchema if hasattr(tool, "inputSchema") else {}
                }
                for tool in result.tools
            ]
            return self.tools_cache
        except Exception as e:
            self.connected = False
            self.last_error = str(e)
            raise RuntimeError(f"Failed to list tools: {e}")

    async def describe_tool(self, tool_name: str) -> Optional[dict]:
        """Get detailed description of a specific tool."""
        tools = await self.list_tools()
        for tool in tools:
            if tool["name"] == tool_name:
                return tool
        return None

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool on the MCP server."""
        if not await self.ensure_connected():
            raise RuntimeError(f"Not connected to MCP server: {self.last_error}")

        try:
            logger.info(f"Calling tool: {tool_name}")
            result = await self.session.call_tool(tool_name, arguments)
            return result.content
        except Exception as e:
            self.connected = False
            self.last_error = str(e)
            raise RuntimeError(f"Tool call failed: {e}")

    async def shutdown(self):
        """Gracefully shutdown the daemon."""
        logger.info("Shutting down daemon...")
        self.running = False

        if self.timeout_task:
            self.timeout_task.cancel()
            try:
                await self.timeout_task
            except asyncio.CancelledError:
                pass

        if self.reconnect_task:
            self.reconnect_task.cancel()
            try:
                await self.reconnect_task
            except asyncio.CancelledError:
                pass

        if self.exit_stack:
            try:
                await self.exit_stack.aclose()
            except Exception as e:
                logger.warning(f"Error during shutdown: {e}")

        self.session = None
        self.connected = False

        # Remove PID file
        if PID_FILE.exists():
            try:
                PID_FILE.unlink()
            except Exception:
                pass

        logger.info("Daemon shutdown complete")

    def get_status(self) -> dict:
        """Get daemon status information."""
        uptime = None
        if self.connection_time:
            uptime = time.time() - self.connection_time

        return {
            "running": self.running,
            "connected": self.connected,
            "uptime_seconds": uptime,
            "last_error": self.last_error,
            "tools_cached": self.tools_cache is not None,
            "pid": os.getpid()
        }


# Global daemon instance
daemon = MCPDaemonService()


# HTTP API Handlers

async def handle_health(request):
    """Health check endpoint."""
    status = daemon.get_status()
    return web.json_response(status)


async def handle_list_tools(request):
    """List available tools."""
    try:
        tools = await daemon.list_tools()
        return web.json_response({"tools": tools})
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_describe_tool(request):
    """Describe a specific tool."""
    try:
        tool_name = request.match_info.get("name")
        if not tool_name:
            return web.json_response({"error": "Missing tool name"}, status=400)

        tool = await daemon.describe_tool(tool_name)
        if tool is None:
            return web.json_response({"error": f"Tool not found: {tool_name}"}, status=404)

        return web.json_response({"tool": tool})
    except Exception as e:
        logger.error(f"Error describing tool: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_call_tool(request):
    """Call a tool."""
    try:
        data = await request.json()
        tool_name = data.get("tool")
        arguments = data.get("arguments", {})

        if not tool_name:
            return web.json_response({"error": "Missing 'tool' parameter"}, status=400)

        result = await daemon.call_tool(tool_name, arguments)

        # Format result for JSON response
        formatted_result = []
        if isinstance(result, list):
            for item in result:
                if hasattr(item, 'text'):
                    formatted_result.append({"type": "text", "content": item.text})
                elif hasattr(item, '__dict__'):
                    formatted_result.append(item.__dict__)
                else:
                    formatted_result.append(str(item))
        else:
            formatted_result = [str(result)]

        return web.json_response({"result": formatted_result})

    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error calling tool: {e}")
        import traceback
        traceback.print_exc()
        return web.json_response({"error": str(e)}, status=500)


async def handle_shutdown(request):
    """Shutdown the daemon."""
    asyncio.create_task(shutdown_server())
    return web.json_response({"message": "Shutting down..."})


async def shutdown_server():
    """Shutdown the server after a short delay."""
    await asyncio.sleep(0.5)
    await daemon.shutdown()
    raise web.GracefulExit()


def write_pid_file():
    """Write PID file for process management."""
    pid = os.getpid()
    PID_FILE.write_text(str(pid))
    logger.info(f"PID file written: {PID_FILE} (PID: {pid})")


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(daemon.shutdown())

    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGHUP, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


async def start_server():
    """Start the HTTP API server."""
    app = web.Application()

    # Routes
    app.router.add_get("/health", handle_health)
    app.router.add_get("/tools", handle_list_tools)
    app.router.add_get("/tools/{name}", handle_describe_tool)
    app.router.add_post("/call", handle_call_tool)
    app.router.add_post("/shutdown", handle_shutdown)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, DAEMON_HOST, DAEMON_PORT)
    await site.start()

    logger.info(f"HTTP API server started on http://{DAEMON_HOST}:{DAEMON_PORT}")
    return runner


async def check_timeout():
    """Check for inactivity timeout and shutdown if exceeded."""
    if DAEMON_TIMEOUT <= 0:
        return  # No timeout configured

    while daemon.running:
        await asyncio.sleep(60)  # Check every minute
        if daemon.last_activity:
            idle_time = time.time() - daemon.last_activity
            if idle_time > DAEMON_TIMEOUT:
                logger.info(f"Idle timeout ({DAEMON_TIMEOUT}s) exceeded, shutting down...")
                await shutdown_server()
                return


async def main():
    """Main entry point."""
    # Write PID file
    write_pid_file()

    # Setup signal handlers
    setup_signal_handlers()

    # Connect to MCP server
    daemon.running = True
    if not await daemon.connect():
        logger.error("Failed to establish initial connection")
        # Continue anyway, will retry on requests

    # Start HTTP server
    runner = await start_server()

    # Start timeout checker if configured
    if DAEMON_TIMEOUT > 0:
        daemon.timeout_task = asyncio.create_task(check_timeout())
        logger.info(f"Idle timeout: {DAEMON_TIMEOUT}s")

    logger.info(f"MCP Daemon running on http://{DAEMON_HOST}:{DAEMON_PORT}")
    logger.info("Endpoints: /health, /tools, /tools/<name>, /call, /shutdown")

    # Keep running
    try:
        while daemon.running:
            await asyncio.sleep(1)
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        await daemon.shutdown()
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user")
    except Exception as e:
        logger.error(f"Daemon error: {e}")
        sys.exit(1)
'''
