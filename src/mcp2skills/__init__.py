# MCP2Skills - AI-Powered MCP to Claude Skills Converter

"""
MCP2Skills converts MCP (Model Context Protocol) servers into Claude Skills
following Anthropic's best practices for progressive disclosure and context efficiency.
"""

__version__ = "0.2.0"
__author__ = "junerver"

from mcp2skills.ai_generator import AISkillGenerator
from mcp2skills.config import Settings
from mcp2skills.converter import MCPToSkillConverter

__all__ = ["MCPToSkillConverter", "AISkillGenerator", "Settings"]
