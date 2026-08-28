"""Source location model for Canonical Code IR."""

from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class SourceLocation(BaseModel):
    """Canonical source location tracking line and column ranges in a source file.

    Lines are 1-indexed; columns are 0-indexed.
    """

    model_config = ConfigDict(frozen=True)

    file_path: str | None = None
    start_line: int
    start_column: int
    end_line: int
    end_column: int

    @field_validator("start_line", "end_line")
    @classmethod
    def validate_line(cls, v: int) -> int:
        """Ensure line numbers are 1-indexed positive integers."""
        if v < 1:
            raise ValueError(f"Line numbers must be >= 1, got {v}")
        return v

    @field_validator("start_column", "end_column")
    @classmethod
    def validate_column(cls, v: int) -> int:
        """Ensure column numbers are non-negative integers."""
        if v < 0:
            raise ValueError(f"Column numbers must be >= 0, got {v}")
        return v

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        """Validate line and column range invariants."""
        if self.end_line < self.start_line:
            raise ValueError(
                f"end_line ({self.end_line}) cannot be less than start_line ({self.start_line})"
            )
        if self.end_line == self.start_line and self.end_column < self.start_column:
            raise ValueError(
                f"end_column ({self.end_column}) cannot be less than start_column ({self.start_column}) on same line"
            )
        return self
