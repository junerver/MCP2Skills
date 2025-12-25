# -*- coding: utf-8 -*-
"""Core MCP to Skill converter."""

import asyncio
import json
import sys
import hashlib
from pathlib import Path
from typing import Any, Optional

from rich.console import Console

from mcp2skills.config import Settings
from mcp2skills.ai_generator import AISkillGenerator
from mcp2skills.templates.executor import EXECUTOR_TEMPLATE
from mcp2skills.templates.daemon_executor import DAEMON_EXECUTOR_TEMPLATE
from mcp2skills.templates.daemon_service import DAEMON_SERVICE_TEMPLATE
from mcp2skills.templates.skill_md import generate_skill_md, generate_tools_reference

console = Console()

# Port range for daemon services (avoid common ports)
DAEMON_PORT_BASE = 19900
DAEMON_PORT_MAX = 19999

# Threshold for compact mode (following progressive disclosure principle)
# When tool count exceeds this, use compact SKILL.md with separate references
COMPACT_MODE_THRESHOLD = 10


def generate_daemon_port(server_name: str) -> int:
    """Generate a unique port number for daemon service based on server name."""
    # Use hash to generate consistent port for same server name
    hash_value = int(hashlib.md5(server_name.encode()).hexdigest()[:8], 16)
    port = DAEMON_PORT_BASE + (hash_value % (DAEMON_PORT_MAX - DAEMON_PORT_BASE))
    return port


class MCPToSkillConverter:
    """Convert MCP server configurations to Claude Skills."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings.from_env()
        self.ai_generator = AISkillGenerator(self.settings)

    def is_daemon_mode(self, config: dict[str, Any]) -> bool:
        """Check if the MCP server should run in daemon mode."""
        return config.get("daemon", False) is True

    async def introspect_mcp_server(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        """Connect to MCP server and discover available tools."""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            console.print("[red]Error: mcp package not installed. Run: pip install mcp[/red]")
            return []

        command = config.get("command", "")
        args = config.get("args", [])
        env = config.get("env", {})

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env,
        )

        tools = []
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    tools = [
                        {
                            "name": tool.name,
                            "description": tool.description or "",
                            "inputSchema": tool.inputSchema if hasattr(tool, "inputSchema") else {},
                        }
                        for tool in result.tools
                    ]
        except Exception as e:
            console.print(f"[yellow]Warning: Could not introspect MCP server: {e}[/yellow]")

        return tools

    def convert(
        self,
        config_path: Path,
        output_dir: Optional[Path] = None,
        compact_mode: Optional[bool] = None,
    ) -> Path:
        """Convert a single MCP config to a Claude Skill.
        
        Args:
            config_path: Path to the MCP server config file
            output_dir: Optional output directory for the skill
            compact_mode: If None, auto-detect based on tool count.
                         If True, use compact mode with separate references.
                         If False, include all details in SKILL.md.
        """
        # Load config
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        server_name = config.get("name", config_path.stem)
        skill_name = f"{self.settings.skill_prefix}{server_name}"
        is_daemon = self.is_daemon_mode(config)

        # Determine output directory
        if output_dir is None:
            output_dir = self.settings.output_dir / skill_name
        else:
            # If output_dir is provided, create skill subdirectory within it
            output_dir = output_dir / skill_name
        output_dir.mkdir(parents=True, exist_ok=True)

        mode_str = "[daemon]" if is_daemon else "[standard]"
        console.print(f"[blue]Converting {server_name} {mode_str}...[/blue]")

        # Introspect MCP server
        tools = asyncio.run(self.introspect_mcp_server(config))
        console.print(f"  Found {len(tools)} tools")

        # Enhance tools with AI if available
        if self.ai_generator.is_available():
            console.print("  [green]Using AI to enhance descriptions...[/green]")
            tools = self._enhance_tools(tools)

        # Generate skill files based on mode
        self._generate_skill_md(server_name, tools, output_dir, is_daemon, compact_mode)
        
        if is_daemon:
            daemon_port = generate_daemon_port(server_name)
            console.print(f"  [cyan]Daemon mode enabled (port: {daemon_port})[/cyan]")
            self._generate_daemon_executor(output_dir, daemon_port)
            self._generate_daemon_service(output_dir, daemon_port)
        else:
            self._generate_executor(output_dir)
        
        self._generate_mcp_config(config, output_dir)
        self._generate_package_json(server_name, output_dir, is_daemon)

        console.print(f"[green]Created skill: {output_dir}[/green]")
        return output_dir

    def _enhance_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Enhance tool descriptions using AI."""
        enhanced = []
        for tool in tools:
            # Enhance tool description
            if not tool.get("description") or len(tool.get("description", "")) < 20:
                tool["description"] = self.ai_generator.enhance_tool_description(tool)

            # Enhance parameter descriptions
            schema = tool.get("inputSchema", {})
            properties = schema.get("properties", {})
            for param_name, param_schema in properties.items():
                if not param_schema.get("description"):
                    param_schema["description"] = self.ai_generator.generate_parameter_description(
                        param_name, param_schema, tool.get("name", "")
                    )

            enhanced.append(tool)
        return enhanced

    def _generate_skill_md(
        self,
        server_name: str,
        tools: list[dict[str, Any]],
        output_dir: Path,
        is_daemon: bool = False,
        compact_mode: Optional[bool] = None,
    ) -> None:
        """Generate SKILL.md file.
        
        Args:
            server_name: Name of the MCP server
            tools: List of tool definitions
            output_dir: Output directory for the skill
            is_daemon: Whether to use daemon mode
            compact_mode: If None, auto-detect based on tool count.
                         If True, use compact mode with separate references.
                         If False, include all details in SKILL.md.
        """
        # Auto-detect compact mode based on tool count (progressive disclosure)
        if compact_mode is None:
            compact_mode = len(tools) > COMPACT_MODE_THRESHOLD
        
        if compact_mode:
            console.print(f"  [cyan]Using compact mode ({len(tools)} tools > {COMPACT_MODE_THRESHOLD})[/cyan]")
        
        # Generate description
        if self.ai_generator.is_available():
            description = self.ai_generator.generate_description(server_name, tools)
        else:
            description = self.ai_generator._fallback_description(server_name, tools)

        # Generate examples
        if self.ai_generator.is_available():
            examples = self.ai_generator.generate_examples(server_name, tools)
        else:
            examples = self.ai_generator._fallback_examples(server_name, tools)

        content = generate_skill_md(
            server_name=server_name,
            description=description,
            tools=tools,
            examples=examples,
            is_daemon=is_daemon,
            compact_mode=compact_mode,
        )

        skill_path = output_dir / "SKILL.md"
        skill_path.write_text(content, encoding="utf-8")
        
        # Generate references/tools.md for compact mode
        if compact_mode:
            self._generate_tools_reference(server_name, tools, output_dir)
    
    def _generate_tools_reference(
        self,
        server_name: str,
        tools: list[dict[str, Any]],
        output_dir: Path,
    ) -> None:
        """Generate references/tools.md file with detailed tool documentation."""
        references_dir = output_dir / "references"
        references_dir.mkdir(parents=True, exist_ok=True)
        
        content = generate_tools_reference(server_name, tools)
        
        tools_ref_path = references_dir / "tools.md"
        tools_ref_path.write_text(content, encoding="utf-8")
        console.print(f"  [green]Created references/tools.md[/green]")

    def _generate_executor(self, output_dir: Path) -> None:
        """Generate standard executor.py file."""
        executor_path = output_dir / "executor.py"
        executor_path.write_text(EXECUTOR_TEMPLATE, encoding="utf-8")

    def _generate_daemon_executor(self, output_dir: Path, daemon_port: int) -> None:
        """Generate daemon mode executor.py file."""
        executor_content = DAEMON_EXECUTOR_TEMPLATE.replace("{daemon_port}", str(daemon_port))
        executor_path = output_dir / "executor.py"
        executor_path.write_text(executor_content, encoding="utf-8")

    def _generate_daemon_service(self, output_dir: Path, daemon_port: int) -> None:
        """Generate mcp_daemon.py service file."""
        daemon_content = DAEMON_SERVICE_TEMPLATE.replace("{daemon_port}", str(daemon_port))
        daemon_path = output_dir / "mcp_daemon.py"
        daemon_path.write_text(daemon_content, encoding="utf-8")

    def _generate_mcp_config(self, config: dict[str, Any], output_dir: Path) -> None:
        """Generate mcp-config.json file."""
        config_path = output_dir / "mcp-config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def _generate_package_json(self, server_name: str, output_dir: Path, is_daemon: bool = False) -> None:
        """Generate package.json file."""
        package = {
            "name": f"skill-{server_name}",
            "version": "1.0.0",
            "description": f"Claude Skill for {server_name} MCP server",
            "mode": "daemon" if is_daemon else "standard",
            "dependencies": {
                "mcp": ">=1.0.0"
            }
        }
        
        # Add aiohttp dependency for daemon mode
        if is_daemon:
            package["dependencies"]["aiohttp"] = ">=3.8.0"
        
        package_path = output_dir / "package.json"
        with open(package_path, "w", encoding="utf-8") as f:
            json.dump(package, f, indent=2, ensure_ascii=False)


class BatchConverter:
    """Batch convert multiple MCP servers to Skills."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings.from_env()
        self.converter = MCPToSkillConverter(settings)

    def split_mcp_config(self) -> int:
        """Split mcpservers.json into individual server configs."""
        config_file = self.settings.mcp_config_file
        if not config_file.exists():
            console.print(f"[red]Config file not found: {config_file}[/red]")
            return 0

        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        mcp_servers = data.get("mcpServers", {})
        if not mcp_servers:
            console.print("[yellow]No mcpServers found in config[/yellow]")
            return 0

        # Clean up servers directory before splitting
        if self.settings.servers_dir.exists():
            for old_file in self.settings.servers_dir.glob("*.json"):
                old_file.unlink()

        self.settings.servers_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for server_name, server_config in mcp_servers.items():
            # Skip disabled servers
            if server_config.get("disabled", False):
                console.print(f"  [dim]Skipping disabled: {server_name}[/dim]")
                continue

            # Add name field
            server_config["name"] = server_name

            # Save to individual file
            output_file = self.settings.servers_dir / f"{server_name}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(server_config, f, indent=2, ensure_ascii=False)

            console.print(f"  [green]OK[/green] {server_name}.json")
            count += 1

        console.print(f"\n[green]Split {count} server configs to {self.settings.servers_dir}/[/green]")
        return count

    def convert_all(self, skip_split: bool = False) -> list[Path]:
        """Convert all MCP servers to Skills.
        
        Args:
            skip_split: Skip splitting mcpservers.json
            
        Returns:
            List of output directories for created skills
        """
        # Step 1: Split config if needed
        if not skip_split:
            self.split_mcp_config()

        # Step 2: Find all server configs
        if not self.settings.servers_dir.exists():
            console.print(f"[red]Servers directory not found: {self.settings.servers_dir}[/red]")
            return []

        configs = sorted(self.settings.servers_dir.glob("*.json"))
        if not configs:
            console.print(f"[yellow]No .json files found in {self.settings.servers_dir}[/yellow]")
            return []

        console.print(f"\n[blue]Converting {len(configs)} MCP servers...[/blue]\n")

        # Get compact_mode from settings (can be None for auto-detect)
        compact_mode = getattr(self.settings, 'compact_mode', None)

        # Step 3: Convert each server
        results = []
        for config_path in configs:
            try:
                output_dir = self.converter.convert(config_path, compact_mode=compact_mode)
                results.append(output_dir)
            except Exception as e:
                console.print(f"[red]Failed to convert {config_path.name}: {e}[/red]")

        console.print(f"\n[green]Successfully converted {len(results)}/{len(configs)} servers[/green]")
        return results
