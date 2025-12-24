# -*- coding: utf-8 -*-
"""Core MCP to Skill converter."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

from rich.console import Console

from mcp2skills.config import Settings
from mcp2skills.ai_generator import AISkillGenerator
from mcp2skills.templates.executor import EXECUTOR_TEMPLATE
from mcp2skills.templates.skill_md import generate_skill_md

console = Console()


class MCPToSkillConverter:
    """Convert MCP server configurations to Claude Skills."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings.from_env()
        self.ai_generator = AISkillGenerator(self.settings)

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
    ) -> Path:
        """Convert a single MCP config to a Claude Skill."""
        # Load config
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        server_name = config.get("name", config_path.stem)
        skill_name = f"{self.settings.skill_prefix}{server_name}"

        # Determine output directory
        if output_dir is None:
            output_dir = self.settings.output_dir / skill_name
        else:
            # If output_dir is provided, create skill subdirectory within it
            output_dir = output_dir / skill_name
        output_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"[blue]Converting {server_name}...[/blue]")

        # Introspect MCP server
        tools = asyncio.run(self.introspect_mcp_server(config))
        console.print(f"  Found {len(tools)} tools")

        # Enhance tools with AI if available
        if self.ai_generator.is_available():
            console.print("  [green]Using AI to enhance descriptions...[/green]")
            tools = self._enhance_tools(tools)

        # Generate skill files
        self._generate_skill_md(server_name, tools, output_dir)
        self._generate_executor(output_dir)
        self._generate_mcp_config(config, output_dir)
        self._generate_package_json(server_name, output_dir)

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
    ) -> None:
        """Generate SKILL.md file."""
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
        )

        skill_path = output_dir / "SKILL.md"
        skill_path.write_text(content, encoding="utf-8")

    def _generate_executor(self, output_dir: Path) -> None:
        """Generate executor.py file."""
        executor_path = output_dir / "executor.py"
        executor_path.write_text(EXECUTOR_TEMPLATE, encoding="utf-8")

    def _generate_mcp_config(self, config: dict[str, Any], output_dir: Path) -> None:
        """Generate mcp-config.json file."""
        config_path = output_dir / "mcp-config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def _generate_package_json(self, server_name: str, output_dir: Path) -> None:
        """Generate package.json file."""
        package = {
            "name": f"skill-{server_name}",
            "version": "1.0.0",
            "description": f"Claude Skill for {server_name} MCP server",
            "dependencies": {
                "mcp": ">=1.0.0"
            }
        }
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
        """Convert all MCP servers to Skills."""
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

        # Step 3: Convert each server
        results = []
        for config_path in configs:
            try:
                output_dir = self.converter.convert(config_path)
                results.append(output_dir)
            except Exception as e:
                console.print(f"[red]Failed to convert {config_path.name}: {e}[/red]")

        console.print(f"\n[green]Successfully converted {len(results)}/{len(configs)} servers[/green]")
        return results
