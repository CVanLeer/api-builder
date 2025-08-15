"""
API documentation parsers for various formats.

This module contains parsers that convert different API documentation
formats into our unified internal model.
"""

from typing import Protocol, Any, List
from dataclasses import dataclass


@dataclass
class APISpecification:
    """Unified internal API model."""
    pass  # Agent 2 will implement this


class Parser(Protocol):
    """Protocol for all API documentation parsers."""
    
    def parse(self, source: Any) -> APISpecification:
        """Parse the source into our internal model."""
        ...
    
    def validate(self, spec: APISpecification) -> List[str]:
        """Validate the parsed specification."""
        ...


# Agent 2 will implement specific parsers here