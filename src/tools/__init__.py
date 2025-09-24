"""MCP Tools module.

Tools are functions that can perform actions or computations.
They can modify state and interact with external systems.
"""

from .calculator import CalculatorTool
from .file_operations import FileOperationsTool
from .web_scraper import WebScraperTool

__all__ = [
    "CalculatorTool",
    "FileOperationsTool", 
    "WebScraperTool",
]