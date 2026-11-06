from dataclasses import dataclass
from datetime import date


class DomainAbstain(ValueError):
    """The caller must emit abstain rather than substitute a numeric zero."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Period:
    start: date
    end: date

    def __post_init__(self):
        if (
            type(self.start) is not date
            or type(self.end) is not date
            or self.start > self.end
        ):
            raise DomainAbstain("invalid_period")
