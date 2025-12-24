# MCP2Skills

🚀 AI 驱动的转换器，将 MCP 服务器转换为符合 Anthropic 最佳实践的 Claude Skills。

[English](./README.md) | 简体中文

## 特性

- **AI 增强生成**：使用 LLM 生成高质量的描述、示例和文档
- **Anthropic 最佳实践**：遵循官方技能设计指南，实现渐进式披露
- **90% 上下文节省**：启动时 token 使用从 ~30k 降至 ~100
- **批量转换**：一次转换多个 MCP 服务器
- **OpenAI 兼容**：支持任何 OpenAI 兼容 API（OpenAI、Azure、本地模型）

## 安装

### 使用 uv（推荐）

```bash
# 克隆仓库
git clone https://github.com/junerver/MCP2Skills.git
cd MCP2Skills

# 使用 uv 安装
uv sync

# 运行
uv run mcp2skills --help
```

### 使用 pip

```bash
# 克隆并安装
git clone https://github.com/junerver/MCP2Skills.git
cd MCP2Skills
pip install -e .

# 运行
mcp2skills --help
```

## 快速开始

### 1. 配置 LLM（可选但推荐）

```bash
# 生成示例配置
mcp2skills init

# 编辑 .env 添加 API 密钥
cp .env.example .env
# 编辑 .env: LLM_API_KEY=your-key-here
```

### 2. 转换单个 MCP 服务器

```bash
# 创建 MCP 配置
cat > github.json << 'EOF'
{
  "name": "github",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {"GITHUB_TOKEN": "ghp_your_token"}
}
EOF

# 转换为 Skill
mcp2skills convert github.json -o ./skills/github

# 安装到 Claude
cp -r ./skills/github ~/.claude/skills/
```

### 3. 批量转换多个服务器

```bash
# 准备 mcpservers.json（Roocode/Claude Code/Kilocode 的标准格式）
# 然后运行批量转换
mcp2skills batch

# 或指定路径
mcp2skills batch -c mcpservers.json -o ./skills
```

## 配置

### 环境变量

创建 `.env` 文件（或使用 `mcp2skills init` 生成模板）：

```env
# LLM 配置（用于 AI 增强）
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096

# 路径
MCP_CONFIG_FILE=mcpservers.json
SERVERS_DIR=servers
OUTPUT_DIR=skills

# 选项
USE_AI=true
SKILL_PREFIX=skill-
```

### 使用不同的 LLM 提供商

```env
# OpenAI
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# Azure OpenAI
LLM_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
LLM_MODEL=gpt-4o-mini

# 本地模型（Ollama、LM Studio 等）
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.2

# 其他 OpenAI 兼容 API
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

## MCP 配置文件格式

`mcpservers.json` 文件使用标准的 MCP 服务器配置格式，兼容：

- **Roocode** - AI 编程助手
- **Claude Code** - Anthropic 官方 CLI
- **Kilocode** - AI 开发环境

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
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/允许的路径"],
      "type": "stdio"
    }
  }
}
```

## CLI 命令

```bash
# 显示帮助
mcp2skills --help

# 转换单个服务器
mcp2skills convert <config.json> [-o output_dir] [--no-ai]

# 批量转换
mcp2skills batch [-c mcpservers.json] [-o skills/] [--skip-split] [--no-ai]

# 生成 .env 模板
mcp2skills init [-o .env.example]
```

## 工作原理

```
┌─────────────────────────────────┐
│ MCP 配置 (JSON)                  │
│ - command, args, env            │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ MCP2Skills                      │
│ 1. 内省 MCP 服务器               │
│ 2. AI 增强描述                   │
│ 3. 生成优化的 SKILL.md           │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 生成的 Skill                     │
│ ├── SKILL.md (~100 tokens)      │
│ ├── executor.py                 │
│ ├── mcp-config.json             │
│ └── package.json                │
└─────────────────────────────────┘
```

## 上下文节省

| 模式 | 空闲 | 激活 | 节省 |
|------|------|------|------|
| MCP (20 工具) | ~30k tokens | ~30k tokens | - |
| Skills | ~100 tokens | ~5k tokens | 83-99% |

## 项目结构

```
MCP2Skills/
├── src/mcp2skills/
│   ├── __init__.py
│   ├── cli.py              # CLI 接口
│   ├── config.py           # 配置管理
│   ├── converter.py        # 核心转换逻辑
│   ├── ai_generator.py     # AI 增强
│   └── templates/
│       ├── executor.py     # 执行器模板
│       └── skill_md.py     # SKILL.md 生成器
├── pyproject.toml          # 项目配置
├── .env.example            # 示例配置
└── README.md
```

## 开发

```bash
# 安装开发依赖
uv sync --dev

# 运行测试
uv run pytest

# 类型检查
uv run mypy src/

# 代码检查
uv run ruff check src/
```

## 贡献

欢迎贡献！感兴趣的领域：

- 测试更多 MCP 服务器
- 改进 AI 提示以获得更好的描述
- 添加更多输出格式
- 文档改进

## 致谢

灵感来源：

- [mcp-to-skill-converter](https://github.com/GBSOSS/-mcp-to-skill-converter) - 原始转换器
- [playwright-skill](https://github.com/lackeyjb/playwright-skill) - 渐进式披露模式
- [Anthropic Skills](https://github.com/anthropics/skills) - 官方技能指南

## 许可证

MIT License - 详见 LICENSE 文件
