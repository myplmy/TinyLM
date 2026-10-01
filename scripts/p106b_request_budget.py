"""One logical teacher job shares its pre-existing total request ceiling.

This is not a semantic classifier or a new source of retry allowances.
The initial request, backend/parse recovery and any future approved duplicate
recovery must consume this same object. It never invokes a teacher itself.
"""
from dataclasses import dataclass, field


@dataclass
class RequestBudget:
    maximum: int = 3
    reasons: list[str] = field(default_factory=list)

    def __post_init__(self):
        if type(self.maximum) is not int or not 1 <= self.maximum <= 3:
            raise ValueError("teacher total attempts must stay within the existing 1..3 ceiling")

    @property
    def remaining(self):
        return self.maximum - len(self.reasons)

    def take(self, reason):
        if not isinstance(reason, str) or not reason:
            raise ValueError("request reason required")
        if not self.remaining:
            raise RuntimeError("shared teacher request budget exhausted")
        self.reasons.append(reason)
        return len(self.reasons)

    def attempts(self):
        while self.remaining:
            yield self.take("initial" if not self.reasons else "existing_recovery")
