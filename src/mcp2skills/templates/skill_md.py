"""SKILL.md template generator following Anthropic best practices."""

from typing import Any


def generate_skill_md(
    server_name: str,
    description: str,
    tools: list[dict[str, Any]],
    examples: str,
    is_daemon: bool = False,
    compact_mode: bool = False,
    daemon_timeout: int = 0,
) -> str:
    """Generate SKILL.md content following Anthropic best practices.

    Args:
        server_name: The name of the MCP server
        description: Server description for the frontmatter
        tools: List of tool definitions with their schemas
        examples: Example usage strings
        is_daemon: Whether to use daemon mode execution instructions
        compact_mode: If True, generates compact SKILL.md with separate references file
                     following progressive disclosure principle (recommended for >10 tools)
    """

    # Generate tool documentation
    tool_docs = _generate_tool_docs(tools, compact=compact_mode)

    # Clean description - remove newlines and extra spaces for YAML compatibility
    clean_description = " ".join(description.split())

    # Generate execution instructions based on mode
    if is_daemon:
        execution_section = _generate_daemon_execution_section(daemon_timeout)
    else:
        execution_section = _generate_standard_execution_section()

    # Build the SKILL.md content
    content = f"""---
name: {server_name}
description: >-
  {clean_description}
---

# {server_name}

{_generate_intro(server_name, tools, is_daemon)}

## Available Tools ({len(tools)})

{tool_docs}
{_generate_reference_note(tools, compact_mode)}
## Instructions

{execution_section}

## Examples

{examples}
"""

    return content


def _generate_standard_execution_section() -> str:
    """Generate execution section for standard mode."""
    return """### Execution

Use the executor to interact with tools. The executor automatically handles cross-platform compatibility.

```bash
# List all available tools
python executor.py --list

# Get detailed info about a specific tool
python executor.py --describe <tool_name>

# Execute a tool
python executor.py --call '{"tool": "<tool_name>", "arguments": {...}}'
```

**Note**: On Windows, run from the skill directory or use the full path with forward slashes.

### Error Handling

If execution fails:
1. Verify tool name with `--list`
2. Check parameter format with `--describe <tool_name>`
3. Ensure MCP server dependencies are installed"""


def _generate_daemon_execution_section(daemon_timeout: int = 0) -> str:
    """Generate execution section for daemon mode."""
    timeout_note = ""
    if daemon_timeout > 0:
        hours = daemon_timeout // 3600
        minutes = (daemon_timeout % 3600) // 60
        if hours > 0:
            timeout_note = f"\n- **Auto-shutdown**: Daemon will automatically stop after {hours}h {minutes}m of inactivity"
        else:
            timeout_note = f"\n- **Auto-shutdown**: Daemon will automatically stop after {minutes} minutes of inactivity"

    return f"""### Execution (Daemon Mode)

This skill uses a persistent daemon for faster tool execution. The daemon maintains a long-lived connection to the MCP server, eliminating connection overhead between calls.

```bash
# List all available tools (auto-starts daemon if needed)
python executor.py --list

# Get detailed info about a specific tool
python executor.py --describe <tool_name>

# Execute a tool
python executor.py --call '{"tool": "<tool_name>", "arguments": {...}}'

# Check daemon status
python executor.py --status

# Manually start/stop daemon
python executor.py --start
python executor.py --stop
```

### Daemon Management

- The daemon starts automatically on first tool call
- It runs in the background and persists across multiple calls
- Use `--status` to check if daemon is running
- Use `--stop` to gracefully shutdown the daemon{timeout_note}

### Daemon Lifecycle

**Important**: When you finish using this skill (e.g., completing a task, ending a session, or switching to other work), please stop the daemon to release system resources:

```bash
python executor.py --stop
```

The daemon will automatically restart when needed for future tool calls.

### Error Handling

If execution fails:
1. Check daemon status with `--status`
2. Verify tool name with `--list`
3. Check parameter format with `--describe <tool_name>`
4. If daemon is unresponsive, stop and restart: `--stop` then retry
5. Check `daemon.log` for detailed error messages"""


def _generate_intro(server_name: str, tools: list[dict[str, Any]], is_daemon: bool = False) -> str:
    """Generate a brief introduction."""
    tool_count = len(tools)
    mode_note = " (daemon mode - persistent connection)" if is_daemon else ""
    if tool_count == 1:
        return f"MCP server providing 1 tool for {server_name} operations{mode_note}."
    return f"MCP server providing {tool_count} tools for {server_name} operations{mode_note}."


def _generate_reference_note(tools: list[dict[str, Any]], compact: bool) -> str:
    """Generate a note pointing to the references file if in compact mode."""
    if not compact or len(tools) <= 5:
        return ""
    return """
> **Note**: For detailed parameter documentation, run `python executor.py --describe <tool_name>`
> or see `references/tools.md` for the complete API reference.

"""


def _generate_tool_docs(tools: list[dict[str, Any]], compact: bool = False) -> str:
    """Generate tool documentation with smart grouping.

    Args:
        tools: List of tool definitions
        compact: If True, only show tool names and brief descriptions (no parameters)
    """
    if not tools:
        return "(No tools available)"

    # Group tools by category
    groups = _group_tools(tools)

    lines = []
    for group_name, group_tools in groups.items():
        if group_name and len(groups) > 1:
            lines.append(f"### {group_name}")
            lines.append("")

        for tool in group_tools:
            lines.extend(_format_tool(tool, compact=compact))
            lines.append("")

    return "\n".join(lines).rstrip()


def _group_tools(tools: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group tools by common prefixes or actions."""
    if len(tools) <= 5:
        return {"": tools}

    groups: dict[str, list[dict[str, Any]]] = {}

    # Common action prefixes
    action_prefixes = [
        "create",
        "get",
        "list",
        "update",
        "delete",
        "search",
        "add",
        "remove",
        "set",
        "read",
        "write",
        "edit",
        "push",
        "pull",
        "merge",
        "fork",
        "close",
        "open",
    ]

    for tool in tools:
        name = tool.get("name", "").lower()
        group_name = ""

        # Try to find a matching action prefix
        for prefix in action_prefixes:
            if name.startswith(prefix + "_") or name.startswith(prefix):
                group_name = prefix.capitalize() + " Operations"
                break

        # Fallback: use first word
        if not group_name:
            parts = name.replace("-", "_").split("_")
            if len(parts) > 1:
                group_name = parts[0].capitalize()
            else:
                group_name = "Other"

        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append(tool)

    # Sort groups and merge small ones
    sorted_groups: dict[str, list[dict[str, Any]]] = {}
    other_tools: list[dict[str, Any]] = []

    for name, group_tools in sorted(groups.items()):
        if len(group_tools) >= 2:
            sorted_groups[name] = group_tools
        else:
            other_tools.extend(group_tools)

    if other_tools:
        sorted_groups["Other"] = other_tools

    return sorted_groups


def _format_tool(tool: dict[str, Any], compact: bool = False) -> list[str]:
    """Format a single tool's documentation.

    Args:
        tool: Tool definition dict
        compact: If True, only show name and brief description (no parameters)
    """
    lines = []
    name = tool.get("name", "unknown")
    description = tool.get("description", "")

    # Truncate long descriptions in compact mode
    if compact and description:
        # Keep only the first sentence or first 100 chars
        first_sentence = description.split(". ")[0]
        if len(first_sentence) > 100:
            description = first_sentence[:97] + "..."
        else:
            description = first_sentence + ("." if not first_sentence.endswith(".") else "")

    # Tool header with description
    if description:
        lines.append(f"- `{name}` - {description}")
    else:
        lines.append(f"- `{name}`")

    # In compact mode, skip parameter details
    if compact:
        return lines

    # Parameters (only in non-compact mode)
    schema = tool.get("inputSchema", {})
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    if properties:
        # Required parameters
        req_params = [(k, v) for k, v in properties.items() if k in required]
        opt_params = [(k, v) for k, v in properties.items() if k not in required]

        if req_params:
            lines.append("    - **Required parameters**:")
            for param_name, param_schema in req_params:
                param_type = param_schema.get("type", "any")
                param_desc = param_schema.get("description", "")
                if param_desc:
                    lines.append(f"      - `{param_name}` ({param_type}): {param_desc}")
                else:
                    lines.append(f"      - `{param_name}` ({param_type})")

        if opt_params:
            lines.append("    - **Optional parameters**:")
            for param_name, param_schema in opt_params:
                param_type = param_schema.get("type", "any")
                param_desc = param_schema.get("description", "")
                if param_desc:
                    lines.append(f"      - `{param_name}` ({param_type}): {param_desc}")
                else:
                    lines.append(f"      - `{param_name}` ({param_type})")

    return lines


def generate_tools_reference(
    server_name: str,
    tools: list[dict[str, Any]],
) -> str:
    """Generate a detailed tools reference file for the references/ directory.

    This file contains complete parameter documentation for all tools,
    following the progressive disclosure principle.
    """
    lines = [
        f"# {server_name} - Tools Reference",
        "",
        "Complete API documentation for all available tools.",
        "",
        "## Tools",
        "",
    ]

    for tool in tools:
        name = tool.get("name", "unknown")
        description = tool.get("description", "")

        lines.append(f"### `{name}`")
        lines.append("")
        if description:
            lines.append(description)
            lines.append("")

        schema = tool.get("inputSchema", {})
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        if properties:
            req_params = [(k, v) for k, v in properties.items() if k in required]
            opt_params = [(k, v) for k, v in properties.items() if k not in required]

            if req_params:
                lines.append("**Required Parameters:**")
                lines.append("")
                for param_name, param_schema in req_params:
                    param_type = param_schema.get("type", "any")
                    param_desc = param_schema.get("description", "")
                    lines.append(f"- `{param_name}` ({param_type})")
                    if param_desc:
                        lines.append(f"  - {param_desc}")
                lines.append("")

            if opt_params:
                lines.append("**Optional Parameters:**")
                lines.append("")
                for param_name, param_schema in opt_params:
                    param_type = param_schema.get("type", "any")
                    param_desc = param_schema.get("description", "")
                    default = param_schema.get("default")
                    lines.append(f"- `{param_name}` ({param_type})")
                    if param_desc:
                        lines.append(f"  - {param_desc}")
                    if default is not None:
                        lines.append(f"  - Default: `{default}`")
                lines.append("")
        else:
            lines.append("*No parameters required.*")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)
