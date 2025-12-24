# MCP2Skills

🚀 Convert any MCP server into a Claude Skill with 90% context savings.

English | [简体中文](./README.zh-CN.md)

## Why This Exists

MCP servers load all tool definitions into context at startup. With 20+ tools, that's 30-50k tokens consumed before Claude does any work.

This converter applies the "progressive disclosure" pattern (inspired by [playwright-skill](https://github.com/lackeyjb/playwright-skill)) to any MCP server:
- **Startup**: ~100 tokens (just metadata)
- **When needed**: ~5k tokens (full instructions)
- **Executing**: 0 tokens (runs externally)

## Quick Start

```bash
# 1. Install dependencies
pip install mcp

# 2. Create your MCP config file
cat > my-mcp.json << 'EOF'
{
  "name": "my-service",
  "command": "node",
  "args": ["path/to/mcp-server.js"],
  "env": {"API_TOKEN": "your-token"}
}
EOF

# 3. Convert to Skill
python mcp_to_skill_v2.py \
  --mcp-config my-mcp.json \
  --output-dir ./skills/my-service

# 4. Install to Claude
cp -r skills/my-service ~/.claude/skills/
```

✅ Done! Your MCP server is now a Claude Skill with minimal context usage.

## MCP Config File Format

The `mcpservers.json` file uses the standard MCP server configuration format compatible with:

- **Roocode** - AI coding assistant
- **Claude Code** - Anthropic's official CLI
- **Kilocode** - AI development environment
- Other MCP-compatible tools

### Format Structure

```json
{
  "mcpServers": {
    "server-name": {
      "command": "path/to/executable",
      "args": ["arg1", "arg2"],
      "env": {
        "ENV_VAR": "value"
      },
      "disabled": false,
      "type": "stdio"
    }
  }
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | ✅ | Executable command (node, npx, uvx, etc.) |
| `args` | array | ✅ | Command arguments |
| `env` | object | ❌ | Environment variables for API keys, paths, etc. |
| `disabled` | boolean | ❌ | Set to `true` to temporarily disable a server |
| `type` | string | ❌ | Transport type (usually "stdio") |

### Example: mcpservers.json

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allow"],
      "type": "stdio"
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  }
}
```

### Finding Your Config File

Different tools store this file in different locations:

| Tool | Config Location |
|------|-----------------|
| Roocode | `~/.roocode/mcps.json` |
| Claude Code | `~/.claude/mcp_config.json` |
| Kilocode | `~/.kilocode/mcp_servers.json` |

You can copy any of these files to use as your `mcpservers.json`.

## What It Does

The converter creates an optimized Skill structure:

1. **Reads** your MCP server config
2. **Introspects** the MCP server to discover all tools
3. **Generates** a complete Skill package:
   - `SKILL.md` - Metadata and full tool documentation
   - `executor.py` - Dynamic MCP tool executor
   - `mcp-config.json` - Server configuration
   - `package.json` - Dependencies
4. **Result**: Claude loads only ~100 tokens at startup
5. **When used**: Full instructions (~5k tokens) load on demand
6. **Execution**: Tools run externally via MCP (0 context tokens)

## Context Savings

**Before (MCP)**:
```
20 tools = 30k tokens always loaded
Context available: 170k / 200k = 85%
```

**After (Skills)**:
```
20 skills = 2k tokens metadata
When 1 skill active: 7k tokens
Context available: 193k / 200k = 96.5%
```

## Real Examples

This repository includes working examples in [skills/](skills/):

### DevOps Skill (23 tools)

Complete Youzan DevOps platform integration combining ops-cli and superbus tools.

**Context savings:**

| Metric | MCP Mode | Skill Mode | Savings |
|--------|----------|------------|---------|
| Idle | ~25k tokens | ~150 tokens | 99.4% |
| Active | ~25k tokens | ~8k tokens | 68% |

### Example Configs

- [example-github-mcp.json](example-github-mcp.json) - GitHub MCP server template
- [opscli-config.json](opscli-config.json) - Ops CLI integration
- [superbus-config.json](superbus-config.json) - Deployment bus system

## Works With

Any standard MCP server:

- ✅ @modelcontextprotocol/server-github
- ✅ @modelcontextprotocol/server-slack
- ✅ @modelcontextprotocol/server-filesystem
- ✅ @modelcontextprotocol/server-postgres
- ✅ Custom MCP servers (Node.js, Python, etc.)

## When To Use

**Use this converter when:**

- You have 10+ MCP tools
- Context space is limited
- Most tools won't be used in each conversation
- Tools are independent and don't need cross-tool coordination

**Stick with native MCP when:**

- You have 1-5 tools (minimal context overhead)
- Tools need persistent connections or complex state
- Cross-platform compatibility is critical
- You need real-time bidirectional communication

### Best Approach: Hybrid

- Keep frequently-used core tools as MCP (always available)
- Convert extended toolsets to Skills (loaded on demand)

## Requirements

- Python 3.8+
- `mcp` package: `pip install mcp`

## How It Works

```text
┌──────────────────────────────────┐
│ MCP Config (JSON)                │
│ - command, args, env             │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ mcp_to_skill_v2.py               │
│ - Introspects MCP server         │
│ - Generates optimized structure  │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ Generated Skill Package          │
│ ├── SKILL.md (~100 tokens)       │
│ ├── executor.py (dynamic)        │
│ ├── mcp-config.json              │
│ └── package.json                 │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ Claude Agent                     │
│ - Loads metadata at startup      │
│ - Loads full docs when needed    │
│ - Executes tools via MCP         │
└──────────────────────────────────┘
```

## Usage Examples

### Converting GitHub MCP Server

```bash
# 1. Create MCP config
cat > github.json << 'EOF'
{
  "name": "github",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {"GITHUB_TOKEN": "ghp_your_token"}
}
EOF

# 2. Convert to Skill
python mcp_to_skill_v2.py \
  --mcp-config github.json \
  --output-dir ./skills/github

# 3. Install to Claude
cp -r ./skills/github ~/.claude/skills/
```

### Batch Converting Multiple Servers

Use `batch_convert.py` to convert multiple MCP servers at once:

```bash
# 1. Prepare mcpservers.json with all your MCP servers
# 2. Run batch conversion
python batch_convert.py

# This automatically:
# - Splits mcpservers.json into servers/ directory
# - Batch converts to skills/ directory
# - Generates one Skill per MCP server
```

Or manually convert multiple configs:

```bash
# Convert all configs in a directory
for config in configs/*.json; do
  name=$(basename "$config" .json)
  python mcp_to_skill_v2.py \
    --mcp-config "$config" \
    --output-dir "./skills/$name"
done

# Install all to Claude
cp -r ./skills/* ~/.claude/skills/
```

## Troubleshooting

### "mcp package not found"
```bash
pip install mcp
```

### MCP Server Not Responding

Check your config file:

- Command path is correct (verify with `which node`, `which npx`)
- Environment variables are properly set
- Server binary/package is accessible
- Test MCP server directly first

### Testing the Generated Skill

```bash
cd skills/your-skill

# List tools
python executor.py --list

# Describe a tool
python executor.py --describe tool_name

# Call a tool
python executor.py --call '{"tool": "tool_name", "arguments": {"param": "value"}}'
```

### Windows Encoding Issues

If you encounter encoding errors on Windows, the executor has built-in UTF-8 fixes:

```bash
# Use forward slashes in paths to avoid issues:
python C:/Users/YourUser/.claude/skills/your-skill/executor.py --list

# Or use the Python interpreter directly:
python ~/.claude/skills/your-skill/executor.py --list
```

## Limitations & Status

- **Early stage** - actively seeking feedback
- Requires `mcp` Python package
- Complex authentication flows may need manual adjustments
- Not all MCP servers have been tested (please report issues!)

## Contributing

Contributions welcome! Areas of interest:

- Testing with diverse MCP servers
- Improving error handling and diagnostics
- Adding more real-world examples
- Documentation improvements
- Performance optimizations

Open an issue or submit a PR at [github.com/junerver/MCP2Skills](https://github.com/junerver/MCP2Skills)

## Credits

This project is based on [mcp-to-skill-converter](https://github.com/GBSOSS/-mcp-to-skill-converter) and has been enhanced with additional features and improvements.

Inspired by:

- [mcp-to-skill-converter](https://github.com/GBSOSS/-mcp-to-skill-converter) - Original converter implementation
- [playwright-skill](https://github.com/lackeyjb/playwright-skill) by @lackeyjb - Progressive disclosure pattern
- [Anthropic Claude Skills](https://www.anthropic.com/news/skills) - Skill framework design
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification

## License

MIT License - See LICENSE file for details

## Resources

- [MCP Specification](https://modelcontextprotocol.io/)
- [Claude Skills Documentation](https://www.anthropic.com/news/skills)
- [Example Skills](skills/) in this repository
