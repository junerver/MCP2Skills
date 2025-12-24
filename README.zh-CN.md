# MCP2Skills

🚀 将任何 MCP 服务器转换为 Claude Skill，节省 90% 上下文。

[English](./README.md) | 简体中文

## 为什么存在这个项目

MCP 服务器在启动时会将所有工具定义加载到上下文中。当有 20+ 个工具时，这意味着在 Claude 开始工作前就会消耗 30-50k tokens。

这个转换器将"渐进式披露"模式（灵感来自 [playwright-skill](https://github.com/lackeyjb/playwright-skill)）应用到任何 MCP 服务器：
- **启动时**：约 100 tokens（仅元数据）
- **需要时**：约 5k tokens（完整指令）
- **执行时**：0 tokens（外部运行）

## 快速开始

```bash
# 1. 安装依赖
pip install mcp

# 2. 创建 MCP 配置文件
cat > my-mcp.json << 'EOF'
{
  "name": "my-service",
  "command": "node",
  "args": ["path/to/mcp-server.js"],
  "env": {"API_TOKEN": "your-token"}
}
EOF

# 3. 转换为 Skill
python mcp_to_skill_v2.py \
  --mcp-config my-mcp.json \
  --output-dir ./skills/my-service

# 4. 安装到 Claude
cp -r skills/my-service ~/.claude/skills/
```

✅ 完成！您的 MCP 服务器现在是一个上下文占用极小的 Claude Skill。

## MCP 配置文件格式

`mcpservers.json` 文件使用标准的 MCP 服务器配置格式，兼容以下工具：

- **Roocode** - AI 编程助手
- **Claude Code** - Anthropic 官方 CLI
- **Kilocode** - AI 开发环境
- 其他 MCP 兼容工具

### 格式结构

```json
{
  "mcpServers": {
    "server-name": {
      "command": "可执行文件路径",
      "args": ["参数1", "参数2"],
      "env": {
        "环境变量": "值"
      },
      "disabled": false,
      "type": "stdio"
    }
  }
}
```

### 字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `command` | string | ✅ | 可执行命令（node、npx、uvx 等） |
| `args` | array | ✅ | 命令参数 |
| `env` | object | ❌ | 环境变量（API 密钥、路径等） |
| `disabled` | boolean | ❌ | 设为 `true` 可临时禁用服务器 |
| `type` | string | ❌ | 传输类型（通常为 "stdio"） |

### 示例：mcpservers.json

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_你的token"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/允许的路径"],
      "type": "stdio"
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  }
}
```

### 查找配置文件

不同工具将配置文件存储在不同位置：

| 工具 | 配置文件位置 |
|------|-------------|
| Roocode | `~/.roocode/mcps.json` |
| Claude Code | `~/.claude/mcp_config.json` |
| Kilocode | `~/.kilocode/mcp_servers.json` |

您可以直接复制这些文件作为 `mcpservers.json` 使用。

## 工作原理

转换器创建优化的 Skill 结构：

1. **读取** 您的 MCP 服务器配置
2. **内省** MCP 服务器以发现所有工具
3. **生成** 完整的 Skill 包：
   - `SKILL.md` - 元数据和完整工具文档
   - `executor.py` - 动态 MCP 工具执行器
   - `mcp-config.json` - 服务器配置
   - `package.json` - 依赖项
4. **结果**：Claude 启动时仅加载约 100 tokens
5. **使用时**：完整指令（约 5k tokens）按需加载
6. **执行**：工具通过 MCP 外部运行（0 上下文 tokens）

## 上下文节省

**之前 (MCP)**：
```
20 个工具 = 30k tokens 始终加载
可用上下文: 170k / 200k = 85%
```

**之后 (Skills)**：
```
20 个 skills = 2k tokens 元数据
激活 1 个 skill: 7k tokens
可用上下文: 193k / 200k = 96.5%
```

## 实际示例

此仓库在 [skills/](skills/) 中包含工作示例：

### DevOps Skill（23 个工具）

完整的 Youzan DevOps 平台集成，结合了 ops-cli 和 superbus 工具。

**上下文节省：**

| 指标 | MCP 模式 | Skill 模式 | 节省 |
|------|----------|------------|------|
| 空闲 | ~25k tokens | ~150 tokens | 99.4% |
| 激活 | ~25k tokens | ~8k tokens | 68% |

### 批量转换

使用 `batch_convert.py` 一次性转换多个 MCP 服务器：

```bash
# 1. 准备 mcpservers.json 配置文件（包含所有 MCP 服务器）
# 2. 运行批量转换
python batch_convert.py

# 自动完成：
# - 拆分 mcpservers.json 到 servers/ 目录
# - 批量转换为 skills/ 目录
# - 每个 MCP 服务器生成独立的 Skill
```

## 支持的 MCP 服务器

任何标准 MCP 服务器：

- ✅ @modelcontextprotocol/server-github
- ✅ @modelcontextprotocol/server-slack
- ✅ @modelcontextprotocol/server-filesystem
- ✅ @modelcontextprotocol/server-postgres
- ✅ 自定义 MCP 服务器（Node.js、Python 等）

## 使用场景

**使用此转换器当：**

- 您有 10+ 个 MCP 工具
- 上下文空间有限
- 大多数工具不会在每次对话中使用
- 工具是独立的，不需要跨工具协调

**保持原生 MCP 当：**

- 您有 1-5 个工具（上下文开销最小）
- 工具需要持久连接或复杂状态
- 跨平台兼容性至关重要
- 您需要实时双向通信

### 最佳方案：混合使用

- 将常用的核心工具保持为 MCP（始终可用）
- 将扩展工具集转换为 Skills（按需加载）

## 系统要求

- Python 3.8+
- `mcp` 包：`pip install mcp`

## 工作流程

```text
┌──────────────────────────────────┐
│ MCP 配置 (JSON)                   │
│ - command, args, env              │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ mcp_to_skill_v2.py               │
│ - 内省 MCP 服务器                │
│ - 生成优化的结构                 │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ 生成的 Skill 包                   │
│ ├── SKILL.md (~100 tokens)       │
│ ├── executor.py (动态)           │
│ ├── mcp-config.json              │
│ └── package.json                 │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ Claude Agent                     │
│ - 启动时加载元数据               │
│ - 需要时加载完整文档             │
│ - 通过 MCP 执行工具              │
└──────────────────────────────────┘
```

## 使用示例

### 转换 GitHub MCP 服务器

```bash
# 1. 创建 MCP 配置
cat > github.json << 'EOF'
{
  "name": "github",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {"GITHUB_TOKEN": "ghp_your_token"}
}
EOF

# 2. 转换为 Skill
python mcp_to_skill_v2.py \
  --mcp-config github.json \
  --output-dir ./skills/github

# 3. 安装到 Claude
cp -r ./skills/github ~/.claude/skills/
```

### 批量转换多个服务器

```bash
# 使用 batch_convert.py 一键转换所有 MCP 服务器
python batch_convert.py

# 预览模式（不实际执行）
python batch_convert.py --dry-run

# 跳过拆分步骤（servers/ 目录已存在）
python batch_convert.py --skip-split
```

## 故障排除

### "mcp 包未找到"
```bash
pip install mcp
```

### MCP 服务器无响应

检查您的配置文件：

- 命令路径正确（使用 `which node`、`which npx` 验证）
- 环境变量正确设置
- 服务器二进制/包可访问
- 先直接测试 MCP 服务器

### 测试生成的 Skill

```bash
cd skills/your-skill

# 列出工具
python executor.py --list

# 描述工具
python executor.py --describe tool_name

# 调用工具
python executor.py --call '{"tool": "tool_name", "arguments": {"param": "value"}}'
```

### Windows 编码问题

如果在 Windows 上遇到编码错误，执行器已内置 UTF-8 修复：

```python
# executor.py 自动处理 Windows 控制台编码
# 使用正斜杠路径避免问题：
python C:/Users/YourUser/.claude/skills/your-skill/executor.py --list
```

## 项目状态

- **早期阶段** - 积极寻求反馈
- 需要 `mcp` Python 包
- 复杂的身份验证流程可能需要手动调整
- 并非所有 MCP 服务器都已测试（欢迎报告问题！）

## 贡献

欢迎贡献！感兴趣的领域：

- 测试更多 MCP 服务器
- 改进错误处理和诊断
- 添加更多实际示例
- 文档改进
- 性能优化

提交 issue 或 PR 至 [github.com/junerver/MCP2Skills](https://github.com/junerver/MCP2Skills)

## 致谢

本项目基于 [mcp-to-skill-converter](https://github.com/GBSOSS/-mcp-to-skill-converter)，并增加了额外功能和改进。

灵感来源：

- [mcp-to-skill-converter](https://github.com/GBSOSS/-mcp-to-skill-converter) - 原始转换器实现
- [playwright-skill](https://github.com/lackeyjb/playwright-skill) by @lackeyjb - 渐进式披露模式
- [Anthropic Claude Skills](https://www.anthropic.com/news/skills) - Skill 框架设计
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP 规范

## 许可证

MIT License - 详见 LICENSE 文件

## 资源

- [MCP 规范](https://modelcontextprotocol.io/)
- [Claude Skills 文档](https://www.anthropic.com/news/skills)
- [本仓库中的示例 Skills](skills/)
