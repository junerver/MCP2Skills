# -*- coding: utf-8 -*-
"""CLI interface for MCP2Skills."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from mcp2skills import __version__
from mcp2skills.config import Settings
from mcp2skills.converter import MCPToSkillConverter, BatchConverter

app = typer.Typer(
    name="mcp2skills",
    help="AI-powered converter that transforms MCP servers into Claude Skills",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"mcp2skills version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit"
    ),
):
    """MCP2Skills - Convert MCP servers to Claude Skills."""
    pass


@app.command()
def convert(
    config: Path = typer.Argument(
        ...,
        help="Path to MCP server config file (JSON)",
        exists=True,
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output directory for the skill",
    ),
    no_ai: bool = typer.Option(
        False, "--no-ai",
        help="Disable AI-powered enhancements",
    ),
    env_file: Optional[Path] = typer.Option(
        None, "--env", "-e",
        help="Path to .env file for configuration",
    ),
):
    """Convert a single MCP server config to a Claude Skill."""
    settings = Settings.from_env(env_file)
    settings.use_ai = not no_ai

    if settings.use_ai and not settings.validate_llm_config():
        console.print(
            "[yellow]Warning: AI enhancements disabled (no LLM_API_KEY configured)[/yellow]"
        )
        settings.use_ai = False

    converter = MCPToSkillConverter(settings)
    output_dir = converter.convert(config, output)

    console.print(Panel(
        f"[green]Skill created successfully![/green]\n\n"
        f"Location: {output_dir}\n\n"
        f"To install:\n"
        f"  cp -r {output_dir} ~/.claude/skills/",
        title="Success",
    ))


@app.command()
def batch(
    mcp_config: Optional[Path] = typer.Option(
        None, "--config", "-c",
        help="Path to mcpservers.json file",
    ),
    servers_dir: Optional[Path] = typer.Option(
        None, "--servers-dir", "-s",
        help="Directory containing individual server configs",
    ),
    output_dir: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output directory for generated skills",
    ),
    skip_split: bool = typer.Option(
        False, "--skip-split",
        help="Skip splitting mcpservers.json (use existing servers/)",
    ),
    no_ai: bool = typer.Option(
        False, "--no-ai",
        help="Disable AI-powered enhancements",
    ),
    env_file: Optional[Path] = typer.Option(
        None, "--env", "-e",
        help="Path to .env file for configuration",
    ),
):
    """Batch convert multiple MCP servers to Claude Skills."""
    settings = Settings.from_env(env_file)

    if mcp_config:
        settings.mcp_config_file = mcp_config
    if servers_dir:
        settings.servers_dir = servers_dir
    if output_dir:
        settings.output_dir = output_dir

    settings.use_ai = not no_ai

    if settings.use_ai and not settings.validate_llm_config():
        console.print(
            "[yellow]Warning: AI enhancements disabled (no LLM_API_KEY configured)[/yellow]"
        )
        settings.use_ai = False

    batch_converter = BatchConverter(settings)
    results = batch_converter.convert_all(skip_split=skip_split)

    if results:
        console.print(Panel(
            f"[green]Batch conversion complete![/green]\n\n"
            f"Created {len(results)} skills in {settings.output_dir}/\n\n"
            f"To install all:\n"
            f"  cp -r {settings.output_dir}/* ~/.claude/skills/",
            title="Success",
        ))


@app.command()
def init(
    output: Path = typer.Option(
        Path(".env.example"), "--output", "-o",
        help="Output path for the example .env file",
    ),
):
    """Generate an example .env configuration file."""
    env_content = """# MCP2Skills Configuration
# Copy this file to .env and fill in your values

# LLM Configuration (for AI-powered enhancements)
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096

# Paths
MCP_CONFIG_FILE=mcpservers.json
SERVERS_DIR=servers
OUTPUT_DIR=skills

# Options
USE_AI=true
SKILL_PREFIX=skill-
"""

    output.write_text(env_content, encoding="utf-8")
    console.print(f"[green]Created example config: {output}[/green]")
    console.print("\nTo use:")
    console.print("  1. Copy to .env: cp .env.example .env")
    console.print("  2. Edit .env and add your LLM_API_KEY")
    console.print("  3. Run: mcp2skills batch")


if __name__ == "__main__":
    app()
