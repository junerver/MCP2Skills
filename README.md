# MCP2Skills

🚀 AI-powered converter that transforms MCP servers into Claude Skills following Anthropic best practices.

English | [简体中文](./README.zh-CN.md)

## Features

- **AI-Enhanced Generation**: Uses LLM to generate high-quality descriptions, examples, and documentation
- **Anthropic Best Practices**: Follows official skill design guidelines for progressive disclosure
- **90% Context Savings**: Reduces token usage from ~30k to ~100 tokens at startup
- **Batch Conversion**: Convert multiple MCP servers at once
- **OpenAI-Compatible**: Works with any OpenAI-compatible API (OpenAI, Azure, local models)

## Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/junerver/MCP2Skills.git
cd MCP2Skills

# Install with uv
uv sync

# Run
uv run mcp2skills --help
```

### Using pip

```bash
# Clone and install
git clone https://github.com/junerver/MCP2Skills.git
cd MCP2Skills
pip install -e .

# Run
mcp2skills --help
```

## Quick Start

### 1. Configure LLM (Optional but Recommended)

```bash
# Generate example config
mcp2skills init

# Edit .env with your API key
cp .env.example .env
# Edit .env: LLM_API_KEY=your-key-here
```

### 2. Convert a Single MCP Server

```bash
# Create MCP config
cat > github.json << 'EOF'
{
  "name": "github",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {"GITHUB_TOKEN": "ghp_your_token"}
}
EOF

# Convert to Skill
mcp2skills convert github.json -o ./skills/github

# Install to Claude
cp -r ./skills/github ~/.claude/skills/
```

### 3. Batch Convert Multiple Servers

```bash
# Prepare mcpservers.json (standard format from Roocode/Claude Code/Kilocode)
# Then run batch conversion
mcp2skills batch

# Or specify paths
mcp2skills batch -c mcpservers.json -o ./skills
```

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

## MCP Config File Format

The `mcpservers.json` file uses the standard MCP server configuration format compatible with:

- **Roocode** - AI coding assistant
- **Claude Code** - Anthropic's official CLI
- **Kilocode** - AI development environment

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allow"],
      "type": "stdio"
    }
  }
}
```

## CLI Commands

```bash
# Show help
mcp2skills --help

# Convert single server
mcp2skills convert <config.json> [-o output_dir] [--no-ai]

# Batch convert
mcp2skills batch [-c mcpservers.json] [-o skills/] [--skip-split] [--no-ai]

# Generate .env template
mcp2skills init [-o .env.example]
```

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
│ ├── SKILL.md (~100 tokens)      │
│ ├── executor.py                 │
│ ├── mcp-config.json             │
│ └── package.json                │
└─────────────────────────────────┘
```

## Context Savings

| Mode | Idle | Active | Savings |
|------|------|--------|---------|
| MCP (20 tools) | ~30k tokens | ~30k tokens | - |
| Skills | ~100 tokens | ~5k tokens | 83-99% |

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
│       ├── executor.py     # Executor template
│       └── skill_md.py     # SKILL.md generator
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

Inspired by:

- [mcp-to-skill-converter](https://github.com/GBSOSS/-mcp-to-skill-converter) - Original converter
- [playwright-skill](https://github.com/lackeyjb/playwright-skill) - Progressive disclosure pattern
- [Anthropic Skills](https://github.com/anthropics/skills) - Official skill guidelines

## License

MIT License - See LICENSE file for details
