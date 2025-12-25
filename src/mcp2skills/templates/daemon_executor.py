# -*- coding: utf-8 -*-
"""Daemon Executor template for skills with persistent MCP connections."""

DAEMON_EXECUTOR_TEMPLATE = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Skill Executor (Daemon Mode) - Persistent connection via daemon service.

This executor automatically manages a daemon process that maintains a long-lived
connection to the MCP server. Benefits:
- Faster tool invocation (no connection overhead per call)
- Shared state across multiple calls
- Automatic daemon lifecycle management
"""

import json
import sys
import os
import time
import argparse
import subprocess
import io
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Configuration
SKILL_DIR = Path(__file__).parent
DAEMON_SCRIPT = SKILL_DIR / "mcp_daemon.py"
PID_FILE = SKILL_DIR / ".daemon.pid"
DAEMON_HOST = "127.0.0.1"
DAEMON_PORT = {daemon_port}
DAEMON_URL = f"http://{DAEMON_HOST}:{DAEMON_PORT}"
STARTUP_TIMEOUT = 15  # seconds


class DaemonClient:
    """Client for communicating with MCP daemon service."""
    
    def __init__(self):
        self.base_url = DAEMON_URL
    
    def is_running(self) -> bool:
        """Check if daemon is running and responsive."""
        try:
            response = urlopen(f"{self.base_url}/health", timeout=2)
            data = json.loads(response.read().decode())
            return data.get("running", False)
        except (URLError, HTTPError, TimeoutError, ConnectionRefusedError):
            return False
    
    def start_daemon(self) -> bool:
        """Start the daemon process if not running."""
        if self.is_running():
            return True
        
        print(f"Starting daemon...", file=sys.stderr)
        
        # Check if daemon script exists
        if not DAEMON_SCRIPT.exists():
            print(f"Error: Daemon script not found: {DAEMON_SCRIPT}", file=sys.stderr)
            return False
        
        # Start daemon as background process
        if sys.platform == "win32":
            # Windows: use subprocess with CREATE_NEW_PROCESS_GROUP
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            process = subprocess.Popen(
                [sys.executable, str(DAEMON_SCRIPT)],
                cwd=str(SKILL_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )
        else:
            # Unix: use nohup-like behavior
            process = subprocess.Popen(
                [sys.executable, str(DAEMON_SCRIPT)],
                cwd=str(SKILL_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        
        # Wait for daemon to start
        start_time = time.time()
        while time.time() - start_time < STARTUP_TIMEOUT:
            time.sleep(0.5)
            if self.is_running():
                print(f"Daemon started (PID: {process.pid})", file=sys.stderr)
                return True
        
        print(f"Error: Daemon failed to start within {STARTUP_TIMEOUT}s", file=sys.stderr)
        return False
    
    def stop_daemon(self) -> bool:
        """Stop the daemon process."""
        try:
            req = Request(f"{self.base_url}/shutdown", method="POST")
            urlopen(req, timeout=5)
            print("Daemon shutdown requested", file=sys.stderr)
            return True
        except Exception as e:
            print(f"Error stopping daemon: {e}", file=sys.stderr)
            return False
    
    def get_status(self) -> dict:
        """Get daemon status."""
        try:
            response = urlopen(f"{self.base_url}/health", timeout=5)
            return json.loads(response.read().decode())
        except Exception as e:
            return {"error": str(e), "running": False}
    
    def list_tools(self) -> list:
        """List available tools."""
        if not self.start_daemon():
            raise RuntimeError("Failed to start daemon")
        
        try:
            response = urlopen(f"{self.base_url}/tools", timeout=30)
            data = json.loads(response.read().decode())
            return data.get("tools", [])
        except Exception as e:
            raise RuntimeError(f"Failed to list tools: {e}")
    
    def describe_tool(self, tool_name: str) -> dict:
        """Get detailed description of a tool."""
        if not self.start_daemon():
            raise RuntimeError("Failed to start daemon")
        
        try:
            response = urlopen(f"{self.base_url}/tools/{tool_name}", timeout=30)
            data = json.loads(response.read().decode())
            return data.get("tool", {})
        except HTTPError as e:
            if e.code == 404:
                raise RuntimeError(f"Tool not found: {tool_name}")
            raise RuntimeError(f"Failed to describe tool: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to describe tool: {e}")
    
    def call_tool(self, tool_name: str, arguments: dict) -> list:
        """Call a tool on the MCP server."""
        if not self.start_daemon():
            raise RuntimeError("Failed to start daemon")
        
        try:
            payload = json.dumps({
                "tool": tool_name,
                "arguments": arguments
            }).encode()
            
            req = Request(
                f"{self.base_url}/call",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            
            response = urlopen(req, timeout=120)  # Long timeout for tool execution
            data = json.loads(response.read().decode())
            
            if "error" in data:
                raise RuntimeError(data["error"])
            
            return data.get("result", [])
            
        except HTTPError as e:
            error_body = e.read().decode() if e.fp else str(e)
            try:
                error_data = json.loads(error_body)
                raise RuntimeError(error_data.get("error", str(e)))
            except json.JSONDecodeError:
                raise RuntimeError(f"Tool call failed: {error_body}")
        except Exception as e:
            raise RuntimeError(f"Tool call failed: {e}")


def format_output(obj) -> str:
    """Format output for display."""
    if isinstance(obj, dict):
        if obj.get("type") == "text":
            return obj.get("content", "")
        return json.dumps(obj, indent=2, ensure_ascii=False)
    elif isinstance(obj, str):
        return obj
    else:
        return str(obj)


def main():
    parser = argparse.ArgumentParser(
        description="MCP Skill Executor (Daemon Mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all available tools
  python executor.py --list
  
  # Get detailed info about a tool
  python executor.py --describe take_snapshot
  
  # Call a tool
  python executor.py --call '{"tool": "take_snapshot", "arguments": {}}'
  
  # Check daemon status
  python executor.py --status
  
  # Stop the daemon
  python executor.py --stop
"""
    )
    
    parser.add_argument("--list", action="store_true", help="List available tools")
    parser.add_argument("--describe", metavar="TOOL", help="Describe a specific tool")
    parser.add_argument("--call", metavar="JSON", help="Call a tool with JSON arguments")
    parser.add_argument("--status", action="store_true", help="Show daemon status")
    parser.add_argument("--stop", action="store_true", help="Stop the daemon")
    parser.add_argument("--start", action="store_true", help="Start the daemon")
    
    args = parser.parse_args()
    client = DaemonClient()
    
    try:
        if args.status:
            status = client.get_status()
            print(json.dumps(status, indent=2))
        
        elif args.stop:
            if client.stop_daemon():
                print("Daemon stopped")
            else:
                print("Failed to stop daemon")
                sys.exit(1)
        
        elif args.start:
            if client.start_daemon():
                print("Daemon started")
            else:
                print("Failed to start daemon")
                sys.exit(1)
        
        elif args.list:
            tools = client.list_tools()
            print(f"Available tools ({len(tools)}):\\n")
            for tool in tools:
                print(f"  - {tool['name']}")
                if tool.get('description'):
                    desc = tool['description'][:80] + "..." if len(tool['description']) > 80 else tool['description']
                    print(f"    {desc}")
            print()
        
        elif args.describe:
            tool = client.describe_tool(args.describe)
            print(f"Tool: {tool.get('name', 'unknown')}")
            print(f"Description: {tool.get('description', '(none)')}")
            if tool.get('inputSchema'):
                print(f"Parameters: {json.dumps(tool['inputSchema'], indent=2, ensure_ascii=False)}")
        
        elif args.call:
            call_data = json.loads(args.call)
            tool_name = call_data.get("tool")
            arguments = call_data.get("arguments", {})
            
            if not tool_name:
                print("Error: Missing 'tool' in JSON", file=sys.stderr)
                sys.exit(1)
            
            result = client.call_tool(tool_name, arguments)
            
            for item in result:
                print(format_output(item))
        
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\\nInterrupted", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
'''