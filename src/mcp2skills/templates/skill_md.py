# -*- coding: utf-8 -*-
"""SKILL.md template generator following Anthropic best practices."""

from typing import Any


def generate_skill_md(
    server_name: str,
    description: str,
    tools: list[dict[str, Any]],
    examples: str,
) -> str:
    """Generate SKILL.md content following Anthropic best practices."""

    # Generate tool documentation
    tool_docs = _generate_tool_docs(tools)

    # Build the SKILL.md content
    content = f"""---
name: {server_name}
description: {description}
---

# {server_name}

{_generate_intro(server_name, tools)}

## Available Tools ({len(tools)})

{tool_docs}

## Instructions

### Execution

Use the executor to interact with tools:

```bash
# List all available tools
python executor.py --list

# Get detailed info about a specific tool
python executor.py --describe <tool_name>

# Execute a tool
python executor.py --call '{{"tool": "<tool_name>", "arguments": {{...}}}}'
```

### Error Handling

If execution fails:
1. Verify tool name with `--list`
2. Check parameter format with `--describe <tool_name>`
3. Ensure MCP server dependencies are installed

## Examples

{examples}
"""

    return content


def _generate_intro(server_name: str, tools: list[dict[str, Any]]) -> str:
    """Generate a brief introduction."""
    tool_count = len(tools)
    if tool_count == 1:
        return f"MCP server providing 1 tool for {server_name} operations."
    return f"MCP server providing {tool_count} tools for {server_name} operations."


def _generate_tool_docs(tools: list[dict[str, Any]]) -> str:
    """Generate tool documentation with smart grouping."""
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
            lines.extend(_format_tool(tool))
            lines.append("")

    return "\n".join(lines).rstrip()


def _group_tools(tools: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group tools by common prefixes or actions."""
    if len(tools) <= 5:
        return {"": tools}

    groups: dict[str, list[dict[str, Any]]] = {}

    # Common action prefixes
    action_prefixes = [
        "create", "get", "list", "update", "delete", "search",
        "add", "remove", "set", "read", "write", "edit",
        "push", "pull", "merge", "fork", "close", "open",
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


def _format_tool(tool: dict[str, Any]) -> list[str]:
    """Format a single tool's documentation."""
    lines = []
    name = tool.get("name", "unknown")
    description = tool.get("description", "")

    # Tool header with description
    if description:
        lines.append(f"- `{name}` - {description}")
    else:
        lines.append(f"- `{name}`")

    # Parameters
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
