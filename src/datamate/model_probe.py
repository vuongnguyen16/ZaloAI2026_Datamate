"""CPU-only P1 policy. Importing this module never creates cloud resources."""

import hashlib
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PROFILE = "vuonghungnguyen07"
CUTOFF = datetime(2026, 10, 1, tzinfo=timezone.utc)
MEMORY_BYTES = 30 * 1024**3


def safe_relative(name: str) -> bool:
    return (
        isinstance(name, str)
        and bool(name)
        and not any(c in name for c in "\\:\0")
        and not PurePosixPath(name).is_absolute()
        and all(part not in ("", ".", "..") for part in name.split("/"))
    )


def aware_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


class ProbeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    profile: Literal["vuonghungnguyen07"]
    workspace: Literal["vuonghungnguyen07"]
    budget_usd: float = Field(gt=0, le=30, allow_inf_nan=False)
    estimated_cost_usd: float = Field(gt=0, le=30, allow_inf_nan=False)
    gpu: Literal["RTX-PRO-6000"]
    memory_budget_bytes: Literal[32212254720]
    seed: Literal[0]
    max_model_len: int = Field(ge=512, le=2048)
    max_tokens: int = Field(ge=1, le=256)
    gpu_timeout_seconds: int = Field(ge=1, le=1200)
    startup_timeout_seconds: int = Field(ge=1, le=1200)
    staging_timeout_seconds: int = Field(ge=1, le=3600)

    @model_validator(mode="after")
    def within_budget(self):
        if self.estimated_cost_usd > self.budget_usd:
            raise ValueError("estimated cost exceeds authorized budget")
        return self


class ModelCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    repository: str = Field(pattern=r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
    full_commit_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    parameters: int = Field(gt=0, le=15_000_000_000)
    public_release_date: str
    snapshot_timestamp: str
    license: Literal["Apache-2.0"]
    eligibility_verified: Literal[True]
    files: dict[str, str]
    sources: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def verified_eligibility(self):
        if (
            not re.fullmatch(r"\d{4}-\d{2}-\d{2}", self.public_release_date)
            or date.fromisoformat(self.public_release_date) >= CUTOFF.date()
            or aware_time(self.snapshot_timestamp) >= CUTOFF
        ):
            raise ValueError("weights eligibility cutoff not satisfied")
        if not self.files or any(
            not safe_relative(name) or not re.fullmatch(r"[0-9a-f]{64}", digest)
            for name, digest in self.files.items()
        ):
            raise ValueError("invalid snapshot file inventory")
        if any(not url.startswith("https://") for url in self.sources):
            raise ValueError("official HTTPS sources required")
        return self


def preflight(
    config: ProbeConfig,
    model: ModelCandidate,
    account: dict,
    billing: dict,
    *,
    now: datetime,
    profile_env: str | None,
) -> dict:
    """Check live identity and fresh billing before constructing any transport."""
    if profile_env != PROFILE:
        raise ValueError("explicit project profile required")
    if account.get("workspace") != PROFILE or account.get("user") != PROFILE:
        raise ValueError("live account does not match project workspace/user")
    try:
        available = billing["available_usd"]
        checked = aware_time(billing["checked_at"])
        age = now.astimezone(timezone.utc) - checked
        valid = (
            type(available) in (int, float)
            and math.isfinite(available)
            and available >= config.estimated_cost_usd
            and timedelta(0) <= age <= timedelta(hours=24)
            and billing["source"] in ("user-confirmed", "dashboard")
        )
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError("billing evidence must be fresh and cover estimated cost")
    return {
        "profile": PROFILE,
        "workspace": PROFILE,
        "model_repository": model.repository,
        "model_revision": model.full_commit_revision,
        "model_parameters": model.parameters,
        "budget_usd": config.budget_usd,
        "estimated_cost_usd": config.estimated_cost_usd,
        "billing": dict(billing),
        "checked_at": now.isoformat(),
        "hard_billing_cap": False,
    }


def verify_snapshot(directory: Path, files: dict[str, str]) -> dict[str, str]:
    """Hash every authorized file, refusing missing files and symlink traversal."""
    root = directory.resolve(strict=True)
    if not files:
        raise ValueError("snapshot inventory is empty")
    actual = {}
    for name, expected in files.items():
        if not safe_relative(name):
            raise ValueError("invalid snapshot path")
        path = root / name
        try:
            if any(part.is_symlink() for part in (path, *path.parents) if part != root):
                raise ValueError("snapshot cannot contain symlink paths")
            if root not in path.resolve(strict=True).parents or not path.is_file():
                raise ValueError("snapshot file outside authorized directory")
            with path.open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
        except OSError as exc:
            raise ValueError("snapshot file missing or unreadable") from exc
        if digest != expected:
            raise ValueError("snapshot content hash mismatch")
        actual[name] = digest
    return actual
