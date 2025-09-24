"""MCP Prompts module.

Prompts are reusable templates that help structure interactions with LLMs.
They provide context and guidance for specific tasks.
"""

from .templates import PromptTemplates

__all__ = [
    "PromptTemplates",
]