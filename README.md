# MCP2Skills

🚀 AI-powered converter that transforms MCP servers into Claude Skills following Anthropic best practices.

English | [简体中文](./README.zh-CN.md)

## Features

- **AI-Enhanced Generation**: Uses LLM to generate high-quality descriptions, examples, and documentation
- **Anthropic Best Practices**: Follows official skill design guidelines for progressive disclosure
- **90% Context Savings**: Reduces token usage from ~30k to ~100 tokens at startup
- **Compact Mode**: Automatically optimizes SKILL.md for tools >10, reducing file size by 60%
- **Daemon Mode Support**: Persistent connections for tools requiring long-lived sessions (e.g., browser automation)
- **Batch Conversion**: Convert multiple MCP servers at once
- **OpenAI-Compatible**: Works with any OpenAI-compatible API (OpenAI, Azure, local models)

## Installation

### 🌟 Quick Install (For All Users)

If you're **not a Python user** or want the simplest installation, we recommend [uv](https://docs.astral.sh/uv/) - a fast Python package manager that handles Python automatically:

#### Windows Users

```powershell
# 1. Install uv (will handle Python automatically)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. Clone and enter project
git clone https://github.com/junerver/MCP2Skills.git
cd MCP2Skills

# 3. Install dependencies (uv downloads Python automatically)
uv sync

# 4. Run
uv run mcp2skills --help
```

#### macOS/Linux Users

```bash
# 1. Install uv (will handle Python automatically)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and enter project
git clone https://github.com/junerver/MCP2Skills.git
cd MCP2Skills

# 3. Install dependencies (uv downloads Python automatically)
uv sync

# 4. Run
uv run mcp2skills --help
```

### 🐍 Traditional Way for Python Users

If you already have Python and are familiar with pip:

```bash
# Clone and install
git clone https://github.com/junerver/MCP2Skills.git
cd MCP2Skills
pip install -e .

# Run
mcp2skills --help
```

> **Note**: When using uv, prefix all commands with `uv run` (e.g., `uv run mcp2skills`). With pip installation, you can run `mcp2skills` directly.

## Quick Start

### 1️⃣ Configure LLM (Optional but Highly Recommended)

AI-enhanced mode automatically generates high-quality tool descriptions and examples, improving skill quality.

```bash
# Generate config template
uv run mcp2skills init    # If using uv
# or
mcp2skills init            # If using pip

# Copy and edit config file
cp .env.example .env
# Set in .env: LLM_API_KEY=your-api-key-here
```

**Supported LLM Providers**: OpenAI, Azure OpenAI, DeepSeek, local models (Ollama/LM Studio), any OpenAI-compatible API.

> 💡 **Skip AI Enhancement**: If you don't want to configure LLM, add `--no-ai` flag to conversion commands.

### 2️⃣ Convert a Single MCP Server

Here's an example using the GitHub server:

**Step 1: Create MCP config file**

Create `github.json` file (Windows users can use Notepad):

```json
{
  "name": "github",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {
    "GITHUB_TOKEN": "ghp_your_actual_token_here"
  }
}
```

**Step 2: Run conversion**

```bash
# uv users
uv run mcp2skills convert github.json -o ./skills/github

# pip users
mcp2skills convert github.json -o ./skills/github
```

**Step 3: Install to Claude**

```bash
# Windows (PowerShell)
Copy-Item -Recurse -Force ./skills/github $env:USERPROFILE\.claude\skills\

# macOS/Linux
cp -r ./skills/github ~/.claude/skills/
```

Done! Restart Claude Desktop to use the skill.

### 3️⃣ Batch Convert Multiple Servers

If you use Roocode, Claude Code, or Kilocode and already have `mcpservers.json`:

```bash
# uv users
uv run mcp2skills batch

# pip users
mcp2skills batch

# Custom paths
uv run mcp2skills batch -c path/to/mcpservers.json -o ./my-skills
```

This automatically converts all MCP servers in the config file.

## Configuration

### Environment Variables

Create a `.env` file (or use `mcp2skills init` to generate a template):

```env
# LLM Configuration (for AI-powered enhancements)
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=60000

# Paths
MCP_CONFIG_FILE=mcpservers.json
SERVERS_DIR=servers
OUTPUT_DIR=skills

# Options
USE_AI=true
SKILL_PREFIX=skill-
```

### Using Different LLM Providers

```env
# OpenAI
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# Azure OpenAI
LLM_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
LLM_MODEL=gpt-4o-mini

# Local (Ollama, LM Studio, etc.)
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.2

# Other OpenAI-compatible APIs
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

## Daemon Mode

For MCP servers that require persistent connections (e.g., browser automation tools like chrome-devtools), you can enable daemon mode by adding `"daemon": true` to the server configuration:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["chrome-devtools-mcp@latest"],
      "daemon": true, // Enable daemon mode
      "daemon_timeout": 3600 // Auto-shutdown after 1 hour of inactivity (optional)
    }
  }
}
```

### Daemon Lifecycle Management

The daemon process persists after the AI session ends. Two mechanisms handle cleanup:

1. **AI-Prompted Shutdown**: SKILL.md instructs AI to run `python executor.py --stop` when finishing tasks
2. **Auto-Timeout**: Configure `daemon_timeout` (seconds) for automatic shutdown after inactivity
   - `0` or omitted = no timeout (manual shutdown only)
   - Example: `3600` = shutdown after 1 hour idle

When daemon mode is enabled, MCP2Skills generates:

- **`mcp_daemon.py`** - HTTP daemon service that maintains a persistent MCP connection
- **`executor.py`** - Daemon-aware executor with automatic lifecycle management

### Benefits of Daemon Mode

| Aspect     | Standard Mode        | Daemon Mode            |
| ---------- | -------------------- | ---------------------- |
| Connection | New per call (~2-5s) | Persistent (<100ms)    |
| Memory     | On-demand            | Resident process       |
| Best For   | Simple tools         | Stateful operations    |
| State      | Lost between calls   | Preserved across calls |

### Daemon Management

```bash
# Check daemon status
python executor.py --status

# Manually start daemon
python executor.py --start

# Stop daemon
python executor.py --stop

# Call tools (auto-starts daemon if needed)
python executor.py --call '{"tool": "take_snapshot", "arguments": {}}'
```

## MCP Config File Format

The `mcpservers.json` file uses the standard MCP server configuration format compatible with:

- **Roocode** - AI coding assistant
- **Claude Code** - Anthropic's official CLI
- **Kilocode** - AI development environment

### Supported Transport Types

MCP2Skills supports all three official MCP transport types:

#### 1. stdio (Local Process)

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token"
      },
      "type": "stdio"
    }
  }
}
```

#### 2. SSE (Server-Sent Events)

```json
{
  "mcpServers": {
    "example-sse": {
      "url": "https://api.example.com/sse",
      "type": "sse",
      "headers": {
        "Authorization": "Bearer your-token"
      }
    }
  }
}
```

#### 3. streamable-http (Recommended for Production)

```json
{
  "mcpServers": {
    "web-reader": {
      "url": "https://api.example.com/mcp",
      "type": "streamable-http",
      "headers": {
        "X-API-Key": "your-api-key"
      }
    }
  }
}
```

**Note**: Requires MCP SDK >= 1.22.0 for streamable-http support

## Compact Mode (Progressive Disclosure)

For skills with many tools (>10), MCP2Skills automatically enables **compact mode** following Anthropic's progressive disclosure principle:

### What is Compact Mode?

- **SKILL.md**: Contains only tool names and brief descriptions (~60% smaller)
- **references/tools.md**: Complete parameter documentation for all tools
- **Auto-detection**: Enabled when tool count > 10

### Benefits

| Metric         | Before       | After        | Improvement |
| -------------- | ------------ | ------------ | ----------- |
| SKILL.md size  | ~11KB        | ~4.4KB       | **-60%**    |
| SKILL.md lines | 288          | 118          | **-59%**    |
| Context usage  | ~3.7k tokens | ~1.5k tokens | **-59%**    |

### Usage

```bash
# Auto-detect (enabled for >10 tools)
mcp2skills convert servers/github.json

# Force enable compact mode
mcp2skills convert servers/github.json --compact

# Batch conversion with compact mode
mcp2skills batch --compact

# Check tool parameters on demand
python executor.py --describe <tool_name>
```

### Progressive Disclosure Levels

1. **Metadata** (~100 tokens): Always in context - name + description
2. **SKILL.md** (<5k tokens): Loaded when skill triggers - tool overview
3. **references/tools.md**: Loaded on demand - detailed parameters

## CLI Command Reference

### Basic Commands

```bash
# Show help
uv run mcp2skills --help        # uv users
mcp2skills --help               # pip users

# Show version
uv run mcp2skills --version
```

### Conversion Commands

```bash
# Convert a single MCP server
uv run mcp2skills convert <config.json> [options]

Options:
  -o, --output DIR     Output directory (default: ./skills/<name>)
  --no-ai              Disable AI enhancement (no LLM config needed)
  --compact            Force enable compact mode (auto-enabled for >10 tools)

Examples:
  uv run mcp2skills convert github.json
  uv run mcp2skills convert github.json -o ./my-skills --no-ai
```

```bash
# Batch convert multiple servers
uv run mcp2skills batch [options]

Options:
  -c, --config FILE    MCP config file (default: mcpservers.json)
  -o, --output DIR     Output root directory (default: ./skills)
  --skip-split         Don't split config, use original file
  --no-ai              Disable AI enhancement
  --compact            Enable compact mode for all skills

Examples:
  uv run mcp2skills batch
  uv run mcp2skills batch -c my-servers.json -o ./output
  uv run mcp2skills batch --no-ai --compact
```

```bash
# Generate config template
uv run mcp2skills init [options]

Options:
  -o, --output FILE    Output file path (default: .env.example)

Examples:
  uv run mcp2skills init
  uv run mcp2skills init -o .env
```

> 💡 **Tip**: If using pip installation, remove `uv run` prefix from all commands.

## How It Works

```
┌─────────────────────────────────┐
│ MCP Config (JSON)               │
│ - command, args, env            │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ MCP2Skills                      │
│ 1. Introspect MCP server        │
│ 2. AI enhances descriptions     │
│ 3. Generate optimized SKILL.md  │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Generated Skill                 │
│ ├── SKILL.md (~100-1500 tokens) │
│ ├── references/                 │
│ │   └── tools.md (if compact)   │
│ ├── executor.py                 │
│ ├── mcp_daemon.py (if daemon)   │
│ ├── mcp-config.json             │
│ └── package.json                │
└─────────────────────────────────┘
```

## Context Savings

| Mode           | Idle        | Active      | Savings |
| -------------- | ----------- | ----------- | ------- |
| MCP (20 tools) | ~30k tokens | ~30k tokens | -       |
| Skills         | ~100 tokens | ~5k tokens  | 83-99%  |

## Project Structure

```
MCP2Skills/
├── src/mcp2skills/
│   ├── __init__.py
│   ├── cli.py              # CLI interface
│   ├── config.py           # Configuration management
│   ├── converter.py        # Core conversion logic
│   ├── ai_generator.py     # AI-powered enhancements
│   └── templates/
│       ├── executor.py         # Standard executor template
│       ├── daemon_executor.py  # Daemon-aware executor
│       ├── daemon_service.py   # Daemon service template
│       └── skill_md.py         # SKILL.md generator
├── pyproject.toml          # Project configuration
├── .env.example            # Example configuration
└── README.md
```

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/
```

## Contributing

Contributions welcome! Areas of interest:

- Testing with diverse MCP servers
- Improving AI prompts for better descriptions
- Adding more output formats
- Documentation improvements

## Credits

Based on and inspired by:

- [MCP2Skills](https://github.com/YJGGZHK/MCP2Skills) - Original codebase and project foundation
- [mcp-to-skill-converter](https://github.com/GBSOSS/-mcp-to-skill-converter) - Initial converter concept
- [playwright-skill](https://github.com/lackeyjb/playwright-skill) - Progressive disclosure pattern
- [Anthropic Skills](https://github.com/anthropics/skills) - Official skill guidelines

MIT License - See LICENSE file for details
