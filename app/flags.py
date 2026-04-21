"""Feature-flag registry for Horizon-based rollouts.

Each horizon task can be merged behind a flag and enabled per pilot town.
Values come from environment variables prefixed with ``BEARSMART_FLAG_``.

References: IMPLEMENTATION_PLAN.md §0.2.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Iterable

# Keep additions in sync with IMPLEMENTATION_PLAN.md §0.2.
_DEFAULTS: dict[str, bool] = {
    # Horizon 1
    "emergency_gate": True,
    "geo_fuzz": True,
    # Horizon 2
    "trip_mode": False,
    "town_pages_v2": False,
    # Horizon 3
    "admin_nudges": False,
    "seasonal_campaigns": False,
}

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _env_key(name: str) -> str:
    return f"BEARSMART_FLAG_{name.upper()}"


def _read(name: str, default: bool) -> bool:
    raw = os.environ.get(_env_key(name))
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in _TRUE:
        return True
    if normalized in _FALSE:
        return False
    return default


@dataclass(frozen=True)
class FlagSet:
    flags: dict[str, bool] = field(default_factory=dict)

    def is_enabled(self, name: str) -> bool:
        return bool(self.flags.get(name, False))

    def as_dict(self) -> dict[str, bool]:
        return dict(self.flags)


def current_flags() -> FlagSet:
    """Snapshot flags from the current environment.

    Called per-request so operators can toggle flags without restarting the
    process in dev; production deployments restart on env changes anyway.
    """
    return FlagSet(flags={name: _read(name, default) for name, default in _DEFAULTS.items()})


def default_flag_names() -> Iterable[str]:
    return tuple(_DEFAULTS.keys())
