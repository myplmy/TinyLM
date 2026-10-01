"""One logical teacher job shares its pre-existing total request ceiling.

This is not a semantic classifier or a new source of retry allowances.
The initial request, backend/parse recovery and any future approved duplicate
recovery must consume this same object. It never invokes a teacher itself.
"""
class RequestBudget:
    def __init__(self, maximum=3):
        if type(maximum) is not int or not 1 <= maximum <= 3:
            raise ValueError("teacher total attempts must stay within the existing 1..3 ceiling")
        self._maximum, self._reasons = maximum, []

    @property
    def maximum(self):
        return self._maximum

    @property
    def reasons(self):
        return tuple(self._reasons)

    @property
    def remaining(self):
        return self.maximum - len(self.reasons)

    def take(self, reason):
        if not isinstance(reason, str) or not reason:
            raise ValueError("request reason required")
        if not self.remaining:
            raise RuntimeError("shared teacher request budget exhausted")
        self._reasons.append(reason)
        return len(self._reasons)

    def attempts(self):
        while self.remaining:
            yield self.take("initial" if not self.reasons else "existing_recovery")
