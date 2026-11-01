"""Observed question schema and submission shape from the supplied guideline.

The organizer's evaluator is not present; this is structural validation, not scoring.
"""

import math
import re
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str
    business_id: str
    question: str
    as_of_date: str

    @field_validator("id", "business_id", "question")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("as_of_date")
    @classmethod
    def iso_date(cls, value: str) -> str:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("as_of_date must be YYYY-MM-DD")
        date.fromisoformat(value)
        return value


AnswerType = Literal[
    "number",
    "percent",
    "string",
    "date",
    "boolean",
    "list",
    "table",
    "unanswerable",
    "abstain",
]


def finite_number(value: Any) -> bool:
    return type(value) in (int, float) and (type(value) is int or math.isfinite(value))


def cell(value: Any) -> bool:
    return isinstance(value, str) or finite_number(value)


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str
    type: AnswerType
    answer: Any = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "Submission":
        if not self.id.strip():
            raise ValueError("id must not be empty")
        value = self.answer
        if self.type in ("unanswerable", "abstain"):
            valid = value is None
        elif self.type in ("number", "percent"):
            valid = finite_number(value)
        elif self.type == "boolean":
            valid = type(value) is bool
        elif self.type == "string":
            valid = isinstance(value, str)
        elif self.type == "date":
            valid = isinstance(value, str) and bool(
                re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", value)
            )
            if valid:
                date.fromisoformat(value if len(value) == 10 else value + "-01")
        elif self.type == "list":
            valid = isinstance(value, list) and all(cell(item) for item in value)
        else:
            valid = (
                isinstance(value, dict)
                and set(value) == {"columns", "rows"}
                and isinstance(value["columns"], list)
                and all(isinstance(c, str) for c in value["columns"])
                and isinstance(value["rows"], list)
                and all(
                    isinstance(row, list)
                    and len(row) == len(value["columns"])
                    and all(cell(item) for item in row)
                    for row in value["rows"]
                )
            )
        if not valid:
            raise ValueError(f"invalid answer for {self.type}")
        return self

    def output(self) -> dict:
        result = {"id": self.id, "type": self.type}
        if self.type not in ("abstain", "unanswerable"):
            result["answer"] = self.answer
        if self.reason is not None:
            result["reason"] = self.reason
        return result


class FakeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    sql: str
    answer_type: Literal["number", "string"]
