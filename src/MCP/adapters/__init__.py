"""
MCP Adapters Module

Model-specific adapters that implement the BaseModel interface
for different scientific models.
"""

from .climada_adapter import ClimadaAdapter
from .lisflood_adapter import LisfloodAdapter

__all__ = [
    "ClimadaAdapter",
    "LisfloodAdapter"
]