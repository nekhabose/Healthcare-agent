"""
LLM provider factory — single place that decides which client to instantiate.
"""
from config import Settings, get_settings
from exceptions import ValidationError

from .base import LLMClient
from .claude import ClaudeClient
from .deepseek import DeepSeekClient


def build_llm_client(settings: Settings | None = None) -> LLMClient:
    """Return the LLMClient implementation specified by config."""
    settings = settings or get_settings()
    provider = settings.llm_provider.lower()

    if provider == "claude":
        return ClaudeClient(
            api_key=settings.anthropic_api_key,
            model=settings.claude_model,
        )
    if provider == "deepseek":
        return DeepSeekClient(
            api_key=settings.deepseek_api_key,
            model=settings.deepseek_model,
            base_url=settings.deepseek_base_url,
        )

    raise ValidationError(
        f"Unknown LLM provider '{settings.llm_provider}'. "
        "Set LLM_PROVIDER to 'claude' or 'deepseek'."
    )
