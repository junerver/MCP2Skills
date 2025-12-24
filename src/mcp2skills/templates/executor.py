# -*- coding: utf-8 -*-
"""Executor template for generated skills."""

EXECUTOR_TEMPLATE = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP Skill Executor - Dynamic tool invocation."""

import json
import sys
import asyncio
import argparse
import io
import os
from pathlib import Path

# Fix Windows console encoding issues
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("Error: mcp package not installed. Run: pip install mcp")
    sys.exit(1)


def load_config() -> dict:
    """Load MCP configuration from mcp-config.json."""
    config_path = Path(__file__).parent / "mcp-config.json"
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


async def get_tools(config: dict) -> list:
    """Get list of available tools from MCP server."""
    server_params = StdioServerParameters(
        command=config.get("command", ""),
        args=config.get("args", []),
        env=config.get("env", {}),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return result.tools


async def call_tool(config: dict, tool_name: str, arguments: dict) -> any:
    """Call a specific tool on the MCP server."""
    server_params = StdioServerParameters(
        command=config.get("command", ""),
        args=config.get("args", []),
        env=config.get("env", {}),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return result.content


def safe_output(obj) -> str:
    """Safely convert object to string for output."""
    try:
        if hasattr(obj, "text"):
            return obj.text
        data = obj.__dict__ if hasattr(obj, "__dict__") else obj
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


def main():
    parser = argparse.ArgumentParser(
        description="MCP Skill Executor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--list", action="store_true", help="List available tools")
    parser.add_argument("--describe", metavar="TOOL", help="Describe a specific tool")
    parser.add_argument("--call", metavar="JSON", help="Call a tool with JSON arguments")

    args = parser.parse_args()
    config = load_config()

    try:
        if args.list:
            tools = asyncio.run(get_tools(config))
            print(f"Available tools ({len(tools)}):\\n")
            for tool in tools:
                print(f"  - {tool.name}")
                if tool.description:
                    desc = tool.description[:80] + "..." if len(tool.description) > 80 else tool.description
                    print(f"    {desc}")
            print()

        elif args.describe:
            tools = asyncio.run(get_tools(config))
            tool = next((t for t in tools if t.name == args.describe), None)
            if not tool:
                print(f"Tool not found: {args.describe}")
                sys.exit(1)

            print(f"Tool: {tool.name}")
            print(f"Description: {tool.description or '(none)'}")
            if hasattr(tool, "inputSchema") and tool.inputSchema:
                print(f"Parameters: {json.dumps(tool.inputSchema, indent=2, ensure_ascii=False)}")

        elif args.call:
            call_data = json.loads(args.call)
            result = asyncio.run(call_tool(
                config,
                call_data["tool"],
                call_data.get("arguments", {})
            ))

            if isinstance(result, list):
                for item in result:
                    print(safe_output(item))
            else:
                print(safe_output(result))

        else:
            parser.print_help()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
