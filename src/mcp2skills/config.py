# -*- coding: utf-8 -*-
"""Configuration management for MCP2Skills."""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from dotenv import load_dotenv


class LLMSettings(BaseModel):
    """LLM API configuration."""

    api_key: str = Field(default="", description="API key for the LLM service")
    base_url: str = Field(
        default="https://api.openai.com/v1",
        description="Base URL for the LLM API"
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="Model name to use for generation"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for generation"
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        description="Maximum tokens for generation"
    )


class Settings(BaseModel):
    """Application settings."""

    # LLM settings
    llm: LLMSettings = Field(default_factory=LLMSettings)

    # Paths
    mcp_config_file: Path = Field(
        default=Path("mcpservers.json"),
        description="Path to MCP servers configuration file"
    )
    servers_dir: Path = Field(
        default=Path("servers"),
        description="Directory for split server configs"
    )
    output_dir: Path = Field(
        default=Path("skills"),
        description="Output directory for generated skills"
    )

    # Generation options
    use_ai: bool = Field(
        default=True,
        description="Use AI to enhance skill generation"
    )
    skill_prefix: str = Field(
        default="skill-",
        description="Prefix for generated skill directories"
    )

    @classmethod
    def from_env(cls, env_file: Optional[Path] = None) -> "Settings":
        """Load settings from environment variables."""
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        llm_settings = LLMSettings(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
        )

        return cls(
            llm=llm_settings,
            mcp_config_file=Path(os.getenv("MCP_CONFIG_FILE", "mcpservers.json")),
            servers_dir=Path(os.getenv("SERVERS_DIR", "servers")),
            output_dir=Path(os.getenv("OUTPUT_DIR", "skills")),
            use_ai=os.getenv("USE_AI", "true").lower() in ("true", "1", "yes"),
            skill_prefix=os.getenv("SKILL_PREFIX", "skill-"),
        )

    def validate_llm_config(self) -> bool:
        """Check if LLM configuration is valid."""
        return bool(self.llm.api_key and self.llm.base_url and self.llm.model)
