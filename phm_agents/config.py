"""Configuration. Dataclass-based to avoid a hard pydantic dependency."""
from __future__ import annotations
import os
from dataclasses import dataclass, field

@dataclass
class Config:
    """Runtime thresholds. Tuned for the synthetic generator, not for real engines."""
    high_risk_threshold: float = 0.65
    medium_risk_threshold: float = 0.40
    anomaly_z_threshold: float = 2.5
    baseline_cycles: int = 10
    max_steps: int = 12
    max_retries: int = 1
    require_approval_for_high_risk: bool = True
    seed: int = 42

    @classmethod
    def from_env(cls) -> "Config":
        """Read overrides from PHM_* env vars, falling back to defaults."""
        c = cls()
        if v := os.getenv("PHM_HIGH_RISK_THRESHOLD"):
            c.high_risk_threshold = float(v)
        if v := os.getenv("PHM_SEED"):
            c.seed = int(v)
        if v := os.getenv("PHM_REQUIRE_APPROVAL"):
            c.require_approval_for_high_risk = v.lower() not in ("0", "false", "no")
        return c
