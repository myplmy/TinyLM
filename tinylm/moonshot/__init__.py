"""Moonshot-branch-only experimental modules.

Production code should depend on a specific PM module, not this package-level
namespace.  That keeps each experiment's transplant/removal boundary explicit.
"""

__all__: list[str] = []
