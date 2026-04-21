"""Geo-fuzz helper that protects private addresses on public surfaces.

Threat T5 (privacy exposure) is existential: publishing exact coordinates for
a livestock or apiary incident reveals a family farm. Every public map render
must route through ``public_point`` before returning coordinates.

References: IMPLEMENTATION_PLAN.md §0.4 and threat T5.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Literal

ReportType = Literal[
    "sighting",
    "attractant_issue",
    "road_crossing",
    "livestock_incident",
    "apiary_incident",
]

# Radius applied to sighting / attractant reports when fuzzing.
_DEFAULT_RADIUS_M = 500.0
# Road crossings are already tied to a road and carry less privacy load but
# we still snap to avoid identifying a specific driveway.
_ROAD_RADIUS_M = 300.0
# Reports that must never leak precise coordinates — the helper returns the
# town centre instead, with no radius exposed.
_STRIP_COORDINATES: frozenset[str] = frozenset(
    {"livestock_incident", "apiary_incident"}
)
_EARTH_RADIUS_M = 6_378_137.0


@dataclass(frozen=True)
class PublicPoint:
    lat: float | None
    lng: float | None
    radius_m: float | None
    stripped: bool = False


def _snap(value: float, step_m: float, axis_m: float) -> float:
    """Snap a coordinate to the nearest ``step_m`` grid cell.

    ``axis_m`` is the metres-per-degree conversion for the relevant axis.
    """
    step_deg = step_m / axis_m
    return round(value / step_deg) * step_deg


def _latitude_step_m() -> float:
    # ~111_132 metres per degree of latitude, stable enough for this purpose.
    return 111_132.0


def _longitude_step_m(latitude: float) -> float:
    return max(1.0, 111_320.0 * math.cos(math.radians(latitude)))


def public_point(
    lat: float | None,
    lng: float | None,
    report_type: str,
    *,
    town_center: tuple[float, float] | None = None,
    jitter_seed: int | None = None,
) -> PublicPoint:
    """Return coordinates safe for public rendering.

    * livestock / apiary → strip coordinates, return only the town centre.
    * anonymous / missing coordinates → return the town centre with no fuzz
      circle (callers should not publish a pseudo-precise report).
    * sightings / attractants → snap to ~500 m grid + broadcast the radius.
    * road crossings → snap to ~300 m grid.
    """
    if report_type in _STRIP_COORDINATES:
        if town_center is None:
            return PublicPoint(lat=None, lng=None, radius_m=None, stripped=True)
        return PublicPoint(
            lat=town_center[0],
            lng=town_center[1],
            radius_m=None,
            stripped=True,
        )

    if lat is None or lng is None:
        if town_center is None:
            return PublicPoint(lat=None, lng=None, radius_m=None)
        return PublicPoint(lat=town_center[0], lng=town_center[1], radius_m=None)

    radius = _ROAD_RADIUS_M if report_type == "road_crossing" else _DEFAULT_RADIUS_M
    lat_step = _latitude_step_m()
    lng_step = _longitude_step_m(lat)
    fuzzed_lat = _snap(lat, radius, lat_step)
    fuzzed_lng = _snap(lng, radius, lng_step)

    if jitter_seed is not None:
        # Deterministic micro-offset stops every report in a cell from stacking
        # on the exact same marker — still well within the published radius.
        rng = random.Random(jitter_seed)
        offset_m = radius * 0.25
        fuzzed_lat += rng.uniform(-offset_m, offset_m) / lat_step
        fuzzed_lng += rng.uniform(-offset_m, offset_m) / lng_step

    return PublicPoint(lat=fuzzed_lat, lng=fuzzed_lng, radius_m=radius)


def haversine_m(lat_a: float, lng_a: float, lat_b: float, lng_b: float) -> float:
    """Great-circle distance in metres. Used by tests."""
    phi_a = math.radians(lat_a)
    phi_b = math.radians(lat_b)
    d_phi = math.radians(lat_b - lat_a)
    d_lambda = math.radians(lng_b - lng_a)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi_a) * math.cos(phi_b) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_RADIUS_M * c
