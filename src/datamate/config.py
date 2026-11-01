from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class SmokeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    adapter: Literal["fake"]
    input_dir: str
    output_root: str
    seed: int = 0
    local_cpu_threads: int = Field(ge=1, le=2)
    memory_limit_mb: int = Field(ge=32, le=256)
    max_fixture_bytes: int = Field(ge=1, le=1048576)
    max_questions: int = Field(ge=1, le=100)


def load_config(path: Path) -> tuple[SmokeConfig, Path, Path]:
    path = path.resolve(strict=True)
    config = SmokeConfig.model_validate(yaml.safe_load(path.read_text("utf-8")))
    input_dir = (path.parent / config.input_dir).resolve(strict=True)
    output_root = (path.parent / config.output_root).resolve()
    if input_dir == output_root or input_dir in output_root.parents:
        raise ValueError("output must be outside input directory")
    expected = (
        "questions.jsonl",
        "sales.csv",
        "responses.json",
        "rulebook.md",
        "calendar.csv",
    )
    size = 0
    for name in expected:
        item = input_dir / name
        if not item.is_file():
            raise ValueError(f"missing fixture file: {name}")
        size += item.stat().st_size
    if size > config.max_fixture_bytes:
        raise ValueError("fixture exceeds local size budget")
    return config, input_dir, output_root
