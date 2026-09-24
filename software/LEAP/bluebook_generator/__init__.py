"""bluebook_generator package.

Public API:
- generate_bluebook: main pipeline to scan KPIs and build the docs.
"""

from .main import generate_bluebook  # re-export for convenience

__all__ = ["generate_bluebook"]
