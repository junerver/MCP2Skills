"""AI-powered skill generator using LLM."""

import json
import os
from typing import Any

from openai import OpenAI
from rich.console import Console

from mcp2skills.config import Settings

console = Console()

# Debug mode from environment
DEBUG = os.getenv("MCP2SKILLS_DEBUG", "").lower() in ("true", "1", "yes")


SYSTEM_PROMPT = """You are an expert at creating AI assistant skills following Anthropic's best practices.

## Core Principles

### Concise is Key
The context window is a public good. Skills share the context window with everything else the AI needs.

**Default assumption: The AI is already very smart.** Only add context it doesn't already have. Challenge each piece of information: "Does the AI really need this explanation?" Prefer concise examples over verbose explanations.

### Description is the Primary Trigger
The `description` field is the ONLY thing the AI reads to decide when to use a skill. It must be:
- Comprehensive enough to trigger correctly
- Include WHAT the skill does AND WHEN to use it
- All "when to use" information goes here, NOT in the body

**Good description example:**
"Comprehensive document creation, editing, and analysis with support for tracked changes, comments, formatting preservation, and text extraction. Use when working with professional documents (.docx files) for: (1) Creating new documents, (2) Modifying or editing content, (3) Working with tracked changes, (4) Adding comments, or any other document tasks"

### Progressive Disclosure
- **Metadata (name + description)**: Always in context (~100 words)
- **SKILL.md body**: Only loaded when skill triggers (<5k words)
- **Bundled resources**: Loaded as needed

## Quality Standards

1. Description must be 50-100 words, comprehensive for triggering
2. Include specific trigger conditions and use cases
3. Parameters should have clear descriptions (never "No description")
4. Examples should use real tool names and realistic parameters
5. Use imperative/infinitive form in instructions
6. Group related tools logically by function

## What NOT to Include

- Verbose explanations the AI already knows
- "When to Use This Skill" sections in body (put in description)
- README.md, INSTALLATION_GUIDE.md, CHANGELOG.md
- Deeply nested references
"""


class AISkillGenerator:
    """AI-powered skill content generator."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client: OpenAI | None = None

        if settings.validate_llm_config():
            self.client = OpenAI(
                api_key=settings.llm.api_key,
                base_url=settings.llm.base_url,
                default_headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
            )

    def is_available(self) -> bool:
        """Check if AI generation is available."""
        return self.client is not None and self.settings.use_ai

    def _debug_log(self, message: str, data: Any = None) -> None:
        """Log debug information if DEBUG mode is enabled."""
        if DEBUG:
            console.print(f"[dim][DEBUG] {message}[/dim]")
            if data:
                console.print(f"[dim]{data}[/dim]")

    def _call_llm(
        self, messages: list[dict], max_tokens: int = 200, temperature: float = None
    ) -> str | None:
        """Make an LLM API call with error handling and debug logging."""
        if not self.client:
            return None

        if temperature is None:
            temperature = self.settings.llm.temperature

        self._debug_log(f"LLM Request to {self.settings.llm.base_url}")
        self._debug_log(
            f"Model: {self.settings.llm.model}, Temperature: {temperature}, Max tokens: {max_tokens}"
        )
        self._debug_log(
            "Messages:", json.dumps(messages, indent=2, ensure_ascii=False)[:500] + "..."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.settings.llm.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            result = response.choices[0].message.content.strip()
            finish_reason = response.choices[0].finish_reason
            self._debug_log(f"LLM Response (full): {result}")
            self._debug_log(f"Finish reason: {finish_reason}")
            if finish_reason == "length":
                console.print(
                    f"[yellow]Warning: AI response was truncated (max_tokens={max_tokens})[/yellow]"
                )
            return result
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            self._debug_log(f"LLM Error Type: {error_type}")
            self._debug_log(f"LLM Error: {error_msg}")

            # Try to get more details from the exception
            if hasattr(e, "response"):
                try:
                    resp = e.response
                    self._debug_log(f"Response Status: {resp.status_code}")
                    self._debug_log(f"Response Body: {resp.text[:500]}")
                except Exception:
                    pass

            console.print(f"[yellow]AI generation failed: {error_msg}, using fallback[/yellow]")
            return None

    def generate_description(self, server_name: str, tools: list[dict[str, Any]]) -> str:
        """Generate an optimized skill description."""
        if not self.is_available():
            return self._fallback_description(server_name, tools)

        tool_summary = self._summarize_tools(tools)

        prompt = f"""Generate a skill description following Anthropic's best practices.

Server Name: {server_name}
Tools Available ({len(tools)}):
{tool_summary}

## CRITICAL LENGTH REQUIREMENT ##
Your response MUST be between 50-100 words. Count your words before responding.
Responses under 50 words will be REJECTED and replaced with a fallback.

## Content Requirements ##
1. Start with what the skill does (capabilities)
2. List 3-5 specific use cases with numbered format: (1), (2), (3)
3. Include relevant keywords for triggering
4. Mention file types or domains if applicable

## Example (75 words) ##
"context7 provides 2 tools for accessing up-to-date software library documentation. Use when you need to: (1) resolve a package or library name to find its documentation ID, (2) fetch current API references and code examples for any library, (3) get conceptual guides and architectural information, (4) look up specific topics like hooks, routing, or authentication. Keywords: documentation, library, package, API, reference, docs."

## Your Response ##
Write a description of 50-100 words for {server_name}. Do not include quotes around your response."""

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        result = self._call_llm(messages, max_tokens=self.settings.llm.max_tokens)

        # Validate length - description should be 50-100 words
        if result:
            word_count = len(result.split())
            if word_count < 30:  # Too short, use fallback
                self._debug_log(f"AI description too short ({word_count} words), using fallback")
                return self._fallback_description(server_name, tools)
            return result
        return self._fallback_description(server_name, tools)

    def enhance_tool_description(self, tool: dict[str, Any]) -> str:
        """Enhance a tool's description using AI."""
        if not self.is_available():
            return tool.get("description", "")

        name = tool.get("name", "unknown")
        original_desc = tool.get("description", "")
        params = tool.get("inputSchema", {}).get("properties", {})

        if original_desc and len(original_desc) > 50:
            return original_desc

        prompt = f"""Improve this MCP tool description.

Tool Name: {name}
Original Description: {original_desc or "(none)"}
Parameters: {json.dumps(params, indent=2)}

Requirements:
1. Write a clear, concise description (1-2 sentences)
2. Explain what the tool does and when to use it
3. If original is good, keep it; if empty/vague, write a better one

Return ONLY the description text."""

        messages = [
            {
                "role": "system",
                "content": "You are a technical writer creating tool documentation.",
            },
            {"role": "user", "content": prompt},
        ]

        result = self._call_llm(messages, max_tokens=500, temperature=0.3)
        return result if result else original_desc

    def generate_parameter_description(
        self, param_name: str, param_schema: dict[str, Any], tool_name: str
    ) -> str:
        """Generate a description for a parameter that lacks one."""
        if not self.is_available():
            return self._infer_param_description(param_name, param_schema)

        prompt = f"""Generate a brief description for this API parameter.

Tool: {tool_name}
Parameter Name: {param_name}
Schema: {json.dumps(param_schema, indent=2)}

Requirements:
1. Write 5-15 words describing what this parameter is for
2. Be specific and actionable
3. Don't start with "The" or "A"

Return ONLY the description text."""

        messages = [{"role": "user", "content": prompt}]
        result = self._call_llm(messages, max_tokens=500, temperature=0.2)
        return result if result else self._infer_param_description(param_name, param_schema)

    def generate_examples(self, server_name: str, tools: list[dict[str, Any]]) -> str:
        """Generate realistic usage examples."""
        if not self.is_available():
            return self._fallback_examples(server_name, tools)

        # Select representative tools
        sample_tools = tools[:3] if len(tools) > 3 else tools
        tool_info = "\n".join(
            [f"- {t.get('name')}: {t.get('description', '')[:100]}" for t in sample_tools]
        )

        prompt = f"""Generate 2-3 realistic bash examples for this skill.

Server: {server_name}
Sample Tools:
{tool_info}

Requirements:
1. Use actual tool names from the list
2. Include realistic parameter values
3. Use the EXACT format: python executor.py --call '{{"tool": "<tool_name>", "arguments": {{...}}}}'
4. Add brief comments explaining each example

Example format:
```bash
# Comment explaining what this does
python executor.py --call '{{"tool": "resolve-library-id", "arguments": {{"libraryName": "react"}}}}'
```

Return ONLY the markdown code block with bash syntax."""

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        result = self._call_llm(messages, max_tokens=self.settings.llm.max_tokens, temperature=0.5)
        return result if result else self._fallback_examples(server_name, tools)

    def _summarize_tools(self, tools: list[dict[str, Any]]) -> str:
        """Create a summary of tools for the prompt."""
        lines = []
        for tool in tools[:10]:  # Limit to avoid token overflow
            name = tool.get("name", "unknown")
            desc = tool.get("description", "")[:80]
            lines.append(f"- {name}: {desc}")
        if len(tools) > 10:
            lines.append(f"... and {len(tools) - 10} more tools")
        return "\n".join(lines)

    def _fallback_description(self, server_name: str, tools: list[dict[str, Any]]) -> str:
        """Generate description without AI."""
        tool_names = [t.get("name", "") for t in tools[:8]]

        # Extract use cases from tool names
        use_cases = []
        for name in tool_names[:5]:
            # Convert tool name to readable use case
            readable = name.replace("_", " ").replace("-", " ")
            use_cases.append(readable)

        # Extract keywords from all tool names
        keywords = set()
        for name in tool_names:
            for word in name.replace("_", " ").replace("-", " ").split():
                if len(word) > 2:  # Skip short words
                    keywords.add(word.lower())

        keywords_str = ", ".join(sorted(keywords)[:8])
        use_cases_str = ", ".join(use_cases[:5]) if use_cases else "various operations"

        return (
            f"{server_name} provides {len(tools)} tools. "
            f"Use cases: {use_cases_str}. "
            f"Keywords: {keywords_str}."
        )

    def _fallback_examples(self, server_name: str, tools: list[dict[str, Any]]) -> str:
        """Generate examples without AI."""
        examples = ["```bash", "# List all tools", "python executor.py --list", ""]

        if tools:
            tool = tools[0]
            tool_name = tool.get("name", "example")
            examples.extend(
                [
                    "# Get tool details",
                    f"python executor.py --describe {tool_name}",
                    "",
                    "# Execute a tool",
                    f'python executor.py --call \'{{"tool": "{tool_name}", "arguments": {{}}}}\'',
                ]
            )

        examples.append("```")
        return "\n".join(examples)

    def _infer_param_description(self, param_name: str, param_schema: dict[str, Any]) -> str:
        """Infer parameter description from name and schema."""
        # Common parameter patterns
        patterns = {
            "owner": "Repository owner (username or organization)",
            "repo": "Repository name",
            "path": "File or directory path",
            "url": "URL to access",
            "query": "Search query string",
            "content": "Content to write or send",
            "message": "Message text",
            "branch": "Git branch name",
            "title": "Title text",
            "body": "Body content or description",
            "name": "Name identifier",
            "id": "Unique identifier",
            "page": "Page number for pagination",
            "per_page": "Number of results per page",
            "state": "Current state or status",
            "sort": "Sort order or field",
        }

        # Check for exact match
        lower_name = param_name.lower()
        if lower_name in patterns:
            return patterns[lower_name]

        # Check for partial match
        for key, desc in patterns.items():
            if key in lower_name:
                return desc

        # Infer from type
        param_type = param_schema.get("type", "")
        if param_type == "array":
            return f"Array of {param_name.rstrip('s')} items"
        elif param_type == "boolean":
            return f"Whether to enable {param_name.replace('_', ' ')}"
        elif param_type == "integer" or param_type == "number":
            return f"Numeric value for {param_name.replace('_', ' ')}"

        return f"Value for {param_name.replace('_', ' ')}"
