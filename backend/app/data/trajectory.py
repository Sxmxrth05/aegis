"""
trajectory.py — Dev A (Phase 2 Workstream A)

Orbital Trajectory & Maneuver Preview Engine.
Provides deterministic, before-and-after propagation arrays for the Trajectory
Simulation screen (/negotiate/:id/trajectory) and timeline scrubber.

Physical model:
- Two-body Keplerian gravity + Earth oblateness (J2 harmonic perturbation)
- 4th-order Runge-Kutta (RK4) numerical integration
- Impulsive delta-v burn dynamics (along-track / prograde / retrograde,
  radial, and normal / cross-track)
- Synchronous before/after state vectors, distance profiles, and geographic
  coordinates (lat/lng/alt) for 3D globe visualization.

Ownership: Dev A
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional, Tuple, List, Dict, Any

from pydantic import BaseModel, Field

try:
    from backend.app.constants import CONJUNCTION_THRESHOLD_KM
    from backend.app.schemas.conjunction import ConjunctionAlert
    from backend.app.schemas.negotiation import Resolution
    from backend.app.schemas.tracked_object import TrackedObject
except ImportError:
    from app.constants import CONJUNCTION_THRESHOLD_KM
    from app.schemas.conjunction import ConjunctionAlert
    from app.schemas.negotiation import Resolution
    from app.schemas.tracked_object import TrackedObject


# ---------------------------------------------------------------------------
# Physical Constants (WGS-84 / EGM-96)
# ---------------------------------------------------------------------------

EARTH_MU = 398600.4418            # km^3 / s^2 (Standard gravitational parameter)
EARTH_RADIUS_KM = 6378.137        # km (WGS-84 equatorial radius)
EARTH_J2 = 1.08262668e-3          # Earth's second zonal harmonic (oblateness)
SECONDS_PER_DAY = 86400.0


# ---------------------------------------------------------------------------
# Pydantic Schemas for Trajectory Data
# ---------------------------------------------------------------------------

class TrajectoryWaypoint(BaseModel):
    """Satellite state at a single timestep along a trajectory."""
    timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp")
    t_seconds: float = Field(..., description="Seconds offset from start of simulation")
    position_km: tuple[float, float, float] = Field(..., description="ECI position (x, y, z) in km")
    velocity_kmps: tuple[float, float, float] = Field(..., description="ECI velocity (vx, vy, vz) in km/s")
    lat: float = Field(..., description="Sub-satellite latitude in degrees (-90 to +90)")
    lng: float = Field(..., description="Sub-satellite longitude in degrees (-180 to +180)")
    alt_km: float = Field(..., description="Altitude above Earth surface in km")


class TrajectoryStep(BaseModel):
    """Synchronous simulation step holding both satellites' nominal and post-maneuver states."""
    timestamp_utc: str
    t_seconds: float
    is_post_burn: bool = Field(..., description="True if this step occurs after maneuver execution")

    # Nominal (no-maneuver / baseline) states
    nominal_primary: TrajectoryWaypoint
    nominal_secondary: TrajectoryWaypoint
    nominal_distance_km: float = Field(..., description="Distance between primary and secondary without maneuver")

    # Post-maneuver states (maneuvering satellite follows altered path after burn)
    maneuvered_primary: TrajectoryWaypoint
    maneuvered_secondary: TrajectoryWaypoint
    maneuvered_distance_km: float = Field(..., description="Distance between satellites under maneuver plan")


class ManeuverTrajectoryResult(BaseModel):
    """Full payload consumed by Dev D's Trajectory Simulation screen and scrubber."""
    conjunction_id: str
    primary_norad_id: str
    primary_name: str
    secondary_norad_id: str
    secondary_name: str
    maneuvering_norad_id: str
    maneuver_type: str
    delta_v_mps: float
    execution_time_utc: str

    # Metrics
    tca_nominal_utc: str
    min_distance_nominal_km: float
    tca_maneuvered_utc: str
    min_distance_maneuvered_km: float
    cleared_threshold: bool = Field(
        ...,
        description="True if post-maneuver minimum distance >= CONJUNCTION_THRESHOLD_KM",
    )

    # Scrubber timeline
    steps: list[TrajectoryStep]

    # Pre-computed path polylines for direct rendering on 3D globe
    nominal_path_primary: list[list[float]] = Field(
        ..., description="List of [lng, lat, alt] coordinates for baseline primary orbit"
    )
    nominal_path_secondary: list[list[float]] = Field(
        ..., description="List of [lng, lat, alt] coordinates for baseline secondary orbit"
    )
    maneuvered_path: list[list[float]] = Field(
        ..., description="List of [lng, lat, alt] coordinates for the maneuvering satellite's altered orbit"
    )


# ---------------------------------------------------------------------------
# Coordinate Transforms & Astrodynamics Math
# ---------------------------------------------------------------------------

def gmst_rad(dt: datetime) -> float:
    """
    Calculate Greenwich Mean Sidereal Time (GMST) in radians for a given UTC datetime.
    Standard IAU formula based on Julian centuries from J2000.0.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    # Julian date
    y = dt.year
    m = dt.month
    d = dt.day + (dt.hour + dt.minute / 60.0 + (dt.second + dt.microsecond / 1e6) / 3600.0) / 24.0

    if m <= 2:
        y -= 1
        m += 12

    a = math.floor(y / 100)
    b = 2 - a + math.floor(a / 4)
    jd = math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5

    t_ut1 = (jd - 2451545.0) / 36525.0
    # GMST in seconds
    theta_sec = (
        67310.54841
        + (876600.0 * 3600.0 + 8640184.812866) * t_ut1
        + 0.093104 * (t_ut1 ** 2)
        - 6.2e-6 * (t_ut1 ** 3)
    )
    theta_rad = (theta_sec % SECONDS_PER_DAY) * (2.0 * math.pi / SECONDS_PER_DAY)
    return theta_rad % (2.0 * math.pi)


def eci_to_geodetic(
    r_eci: tuple[float, float, float],
    dt: datetime,
) -> tuple[float, float, float]:
    """
    Convert ECI position (km) and UTC datetime to Geodetic (lat_deg, lng_deg, alt_km).
    """
    x, y, z = r_eci
    theta = gmst_rad(dt)

    # Rotate ECI into Earth-Centered Earth-Fixed (ECEF)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    x_ecef = x * cos_t + y * sin_t
    y_ecef = -x * sin_t + y * cos_t
    z_ecef = z

    # Longitude (-180 to +180)
    lng_deg = math.degrees(math.atan2(y_ecef, x_ecef))

    # WGS-84 Bowring approximation for Latitude and Altitude
    r_xy = math.sqrt(x_ecef * x_ecef + y_ecef * y_ecef)
    if r_xy < 1e-6:
        lat_deg = 90.0 if z_ecef > 0 else -90.0
        alt_km = abs(z_ecef) - EARTH_RADIUS_KM
        return lat_deg, lng_deg, alt_km

    lat_rad = math.atan2(z_ecef, r_xy)
    # 2 iterations for LEO precision
    for _ in range(3):
        sin_lat = math.sin(lat_rad)
        n = EARTH_RADIUS_KM / math.sqrt(1.0 - 0.00669437999014 * sin_lat * sin_lat)
        lat_rad = math.atan2(z_ecef + 0.00669437999014 * n * sin_lat, r_xy)

    lat_deg = math.degrees(lat_rad)
    sin_lat = math.sin(lat_rad)
    n = EARTH_RADIUS_KM / math.sqrt(1.0 - 0.00669437999014 * sin_lat * sin_lat)
    alt_km = (r_xy / math.cos(lat_rad)) - n if abs(math.cos(lat_rad)) > 1e-4 else (abs(z_ecef) / abs(sin_lat)) - n

    return lat_deg, lng_deg, alt_km


def gravitational_acceleration(
    r: tuple[float, float, float],
) -> tuple[float, float, float]:
    """
    Total gravitational acceleration in ECI (km/s^2) incorporating
    central body two-body gravity and Earth J2 oblateness perturbation.
    """
    x, y, z = r
    r2 = x * x + y * y + z * z
    r_mag = math.sqrt(r2)
    r3 = r2 * r_mag
    r5 = r3 * r2

    # Two-body acceleration
    mu_r3 = -EARTH_MU / r3
    ax_two_body = mu_r3 * x
    ay_two_body = mu_r3 * y
    az_two_body = mu_r3 * z

    # J2 zonal harmonic perturbation
    z2_r2 = (z * z) / r2
    j2_factor = -1.5 * EARTH_J2 * EARTH_MU * (EARTH_RADIUS_KM ** 2) / r5
    ax_j2 = j2_factor * x * (1.0 - 5.0 * z2_r2)
    ay_j2 = j2_factor * y * (1.0 - 5.0 * z2_r2)
    az_j2 = j2_factor * z * (3.0 - 5.0 * z2_r2)

    return (ax_two_body + ax_j2, ay_two_body + ay_j2, az_two_body + az_j2)


def rk4_step(
    r: tuple[float, float, float],
    v: tuple[float, float, float],
    dt: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """
    Classical Runge-Kutta 4th-order (RK4) numerical integrator step.
    Integrates orbital state (r, v) by time interval dt (seconds).
    Works forward (dt > 0) and backward (dt < 0).
    """
    # k1
    a1 = gravitational_acceleration(r)
    dr1 = v
    dv1 = a1

    # k2
    r2 = (r[0] + 0.5 * dt * dr1[0], r[1] + 0.5 * dt * dr1[1], r[2] + 0.5 * dt * dr1[2])
    v2 = (v[0] + 0.5 * dt * dv1[0], v[1] + 0.5 * dt * dv1[1], v[2] + 0.5 * dt * dv1[2])
    a2 = gravitational_acceleration(r2)
    dr2 = v2
    dv2 = a2

    # k3
    r3 = (r[0] + 0.5 * dt * dr2[0], r[1] + 0.5 * dt * dr2[1], r[2] + 0.5 * dt * dr2[2])
    v3 = (v[0] + 0.5 * dt * dv2[0], v[1] + 0.5 * dt * dv2[1], v[2] + 0.5 * dt * dv2[2])
    a3 = gravitational_acceleration(r3)
    dr3 = v3
    dv3 = a3

    # k4
    r4 = (r[0] + dt * dr3[0], r[1] + dt * dr3[1], r[2] + dt * dr3[2])
    v4 = (v[0] + dt * dv3[0], v[1] + dt * dv3[1], v[2] + dt * dv3[2])
    a4 = gravitational_acceleration(r4)
    dr4 = v4
    dv4 = a4

    # Combine
    r_next = (
        r[0] + (dt / 6.0) * (dr1[0] + 2.0 * dr2[0] + 2.0 * dr3[0] + dr4[0]),
        r[1] + (dt / 6.0) * (dr1[1] + 2.0 * dr2[1] + 2.0 * dr3[1] + dr4[1]),
        r[2] + (dt / 6.0) * (dr1[2] + 2.0 * dr2[2] + 2.0 * dr3[2] + dr4[2]),
    )
    v_next = (
        v[0] + (dt / 6.0) * (dv1[0] + 2.0 * dv2[0] + 2.0 * dv3[0] + dv4[0]),
        v[1] + (dt / 6.0) * (dv1[1] + 2.0 * dv2[1] + 2.0 * dv3[1] + dv4[1]),
        v[2] + (dt / 6.0) * (dv1[2] + 2.0 * dv2[2] + 2.0 * dv3[2] + dv4[2]),
    )
    return r_next, v_next


def apply_impulse_burn(
    r: tuple[float, float, float],
    v: tuple[float, float, float],
    maneuver_type: str,
    delta_v_mps: float,
) -> tuple[float, float, float]:
    """
    Applies an impulsive delta-v burn to velocity vector v at position r.
    Supports prograde, retrograde, radial (in/out), and normal / cross-track burns.

    Args:
        r: ECI position (km)
        v: ECI velocity (km/s)
        maneuver_type: 'prograde', 'retrograde', 'radial', 'normal', etc.
        delta_v_mps: Burn magnitude in meters per second.

    Returns:
        New ECI velocity vector (km/s) post-burn.
    """
    dv_kmps = delta_v_mps / 1000.0
    v_mag = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    r_mag = math.sqrt(r[0] ** 2 + r[1] ** 2 + r[2] ** 2)

    if v_mag < 1e-9 or r_mag < 1e-9:
        return v

    # Unit vectors
    # Along-track / Velocity direction
    v_hat = (v[0] / v_mag, v[1] / v_mag, v[2] / v_mag)
    # Radial direction (outward)
    r_hat = (r[0] / r_mag, r[1] / r_mag, r[2] / r_mag)
    # Normal / Orbit angular momentum direction (r x v)
    hx = r[1] * v[2] - r[2] * v[1]
    hy = r[2] * v[0] - r[0] * v[2]
    hz = r[0] * v[1] - r[1] * v[0]
    h_mag = math.sqrt(hx * hx + hy * hy + hz * hz)
    h_hat = (hx / h_mag, hy / h_mag, hz / h_mag) if h_mag > 1e-9 else (0.0, 0.0, 1.0)

    mtype = maneuver_type.lower()
    if "retrograde" in mtype:
        dv_vec = (-dv_kmps * v_hat[0], -dv_kmps * v_hat[1], -dv_kmps * v_hat[2])
    elif "radial_in" in mtype:
        dv_vec = (-dv_kmps * r_hat[0], -dv_kmps * r_hat[1], -dv_kmps * r_hat[2])
    elif "radial" in mtype:
        dv_vec = (dv_kmps * r_hat[0], dv_kmps * r_hat[1], dv_kmps * r_hat[2])
    elif "normal" in mtype or "cross_track" in mtype or "out_of_plane" in mtype:
        dv_vec = (dv_kmps * h_hat[0], dv_kmps * h_hat[1], dv_kmps * h_hat[2])
    else:  # Default: prograde
        dv_vec = (dv_kmps * v_hat[0], dv_kmps * v_hat[1], dv_kmps * v_hat[2])

    return (v[0] + dv_vec[0], v[1] + dv_vec[1], v[2] + dv_vec[2])


def distance_km(r1: tuple[float, float, float], r2: tuple[float, float, float]) -> float:
    """Euclidean distance between two position vectors."""
    return math.sqrt((r1[0] - r2[0]) ** 2 + (r1[1] - r2[1]) ** 2 + (r1[2] - r2[2]) ** 2)


# ---------------------------------------------------------------------------
# Core Generator: Before/After Trajectory Timeline
# ---------------------------------------------------------------------------

def generate_maneuver_trajectory(
    primary: TrackedObject | dict,
    secondary: TrackedObject | dict,
    resolution: Resolution | dict,
    conjunction_alert: ConjunctionAlert | dict | None = None,
    window_minutes: float = 60.0,
    step_seconds: int = 30,
) -> ManeuverTrajectoryResult:
    """
    Generates high-fidelity before-and-after trajectories centered around the
    conjunction event.

    Args:
        primary: Initial state of primary satellite (at or near TCA)
        secondary: Initial state of secondary satellite (at or near TCA)
        resolution: Maneuver resolution specifying delta-v, execution time, and agent
        conjunction_alert: Optional conjunction alert metadata
        window_minutes: Duration of simulation window (e.g. 60 min, ±30 min around TCA)
        step_seconds: Timestep resolution for timeline scrubber (default: 30s)

    Returns:
        ManeuverTrajectoryResult containing full time series, metrics, and 3D paths.
    """
    # Normalize inputs
    if isinstance(primary, dict):
        primary = TrackedObject(**primary)
    if isinstance(secondary, dict):
        secondary = TrackedObject(**secondary)
    if isinstance(resolution, dict):
        resolution = Resolution(**resolution)

    # Conjunction ID and maneuvering NORAD resolution
    conjunction_id = resolution.conjunction_id
    if resolution.maneuvering_agent in ("operator_A", primary.norad_id):
        maneuvering_norad_id = primary.norad_id
    elif resolution.maneuvering_agent in ("operator_B", secondary.norad_id):
        maneuvering_norad_id = secondary.norad_id
    else:
        # Default to primary if ambiguous
        maneuvering_norad_id = primary.norad_id

    # Timing references
    t_ref = datetime.fromisoformat(primary.timestamp_utc.replace("Z", "+00:00")).astimezone(timezone.utc)
    t_burn = datetime.fromisoformat(resolution.execution_time_utc.replace("Z", "+00:00")).astimezone(timezone.utc)

    # Determine simulation start and end times
    # Anchor around t_ref / t_burn so both the burn and closest approach are inside the window
    center_time = min(t_ref, t_burn) + abs(t_ref - t_burn) / 2
    half_window = timedelta(minutes=window_minutes / 2.0)
    start_time = min(t_burn - timedelta(minutes=10), center_time - half_window)
    end_time = max(t_ref + timedelta(minutes=20), center_time + half_window)

    # 1. Propagate Primary & Secondary nominal orbits across [start_time, end_time]
    # First, integrate backward from reference time to start_time
    sec_to_start = (start_time - t_ref).total_seconds()
    r_pri_start, v_pri_start = primary.position_km, primary.velocity_kmps
    r_sec_start, v_sec_start = secondary.position_km, secondary.velocity_kmps

    if sec_to_start < 0:
        # Backward integration to start_time
        num_backward_steps = int(abs(sec_to_start) / step_seconds)
        dt_backward = sec_to_start / max(num_backward_steps, 1)
        curr_r_p, curr_v_p = r_pri_start, v_pri_start
        curr_r_s, curr_v_s = r_sec_start, v_sec_start
        for _ in range(num_backward_steps):
            curr_r_p, curr_v_p = rk4_step(curr_r_p, curr_v_p, dt_backward)
            curr_r_s, curr_v_s = rk4_step(curr_r_s, curr_v_s, dt_backward)
        r_pri_start, v_pri_start = curr_r_p, curr_v_p
        r_sec_start, v_sec_start = curr_r_s, curr_v_s

    # 2. Forward integration from start_time to end_time
    total_duration_sec = (end_time - start_time).total_seconds()
    num_steps = int(total_duration_sec / step_seconds)

    # Maneuver tracking
    primary_maneuvers = (maneuvering_norad_id == primary.norad_id)

    curr_time = start_time
    curr_r_pri_nom, curr_v_pri_nom = r_pri_start, v_pri_start
    curr_r_sec_nom, curr_v_sec_nom = r_sec_start, v_sec_start

    # Maneuvered state begins identical to nominal before burn
    curr_r_pri_man, curr_v_pri_man = r_pri_start, v_pri_start
    curr_r_sec_man, curr_v_sec_man = r_sec_start, v_sec_start

    steps: list[TrajectoryStep] = []
    nominal_path_pri: list[list[float]] = []
    nominal_path_sec: list[list[float]] = []
    maneuvered_path: list[list[float]] = []

    min_dist_nom = float("inf")
    tca_nom_time = start_time
    min_dist_man = float("inf")
    tca_man_time = start_time

    burn_applied = False

    for i in range(num_steps + 1):
        step_time = start_time + timedelta(seconds=i * step_seconds)
        t_sec = i * float(step_seconds)

        # Check burn execution: applies at the first step >= t_burn
        if not burn_applied and step_time >= t_burn:
            burn_applied = True
            if primary_maneuvers:
                curr_v_pri_man = apply_impulse_burn(
                    curr_r_pri_man,
                    curr_v_pri_man,
                    resolution.maneuver_type,
                    resolution.delta_v_mps,
                )
            else:
                curr_v_sec_man = apply_impulse_burn(
                    curr_r_sec_man,
                    curr_v_sec_man,
                    resolution.maneuver_type,
                    resolution.delta_v_mps,
                )

        # Compute geodetics
        lat_pn, lng_pn, alt_pn = eci_to_geodetic(curr_r_pri_nom, step_time)
        lat_sn, lng_sn, alt_sn = eci_to_geodetic(curr_r_sec_nom, step_time)
        lat_pm, lng_pm, alt_pm = eci_to_geodetic(curr_r_pri_man, step_time)
        lat_sm, lng_sm, alt_sm = eci_to_geodetic(curr_r_sec_man, step_time)

        # Distance calculations
        d_nom = distance_km(curr_r_pri_nom, curr_r_sec_nom)
        d_man = distance_km(curr_r_pri_man, curr_r_sec_man)

        if d_nom < min_dist_nom:
            min_dist_nom = d_nom
            tca_nom_time = step_time

        if d_man < min_dist_man:
            min_dist_man = d_man
            tca_man_time = step_time

        # Waypoint models
        nom_pri_wp = TrajectoryWaypoint(
            timestamp_utc=step_time.isoformat(),
            t_seconds=t_sec,
            position_km=curr_r_pri_nom,
            velocity_kmps=curr_v_pri_nom,
            lat=round(lat_pn, 4),
            lng=round(lng_pn, 4),
            alt_km=round(alt_pn, 2),
        )
        nom_sec_wp = TrajectoryWaypoint(
            timestamp_utc=step_time.isoformat(),
            t_seconds=t_sec,
            position_km=curr_r_sec_nom,
            velocity_kmps=curr_v_sec_nom,
            lat=round(lat_sn, 4),
            lng=round(lng_sn, 4),
            alt_km=round(alt_sn, 2),
        )
        man_pri_wp = TrajectoryWaypoint(
            timestamp_utc=step_time.isoformat(),
            t_seconds=t_sec,
            position_km=curr_r_pri_man,
            velocity_kmps=curr_v_pri_man,
            lat=round(lat_pm, 4),
            lng=round(lng_pm, 4),
            alt_km=round(alt_pm, 2),
        )
        man_sec_wp = TrajectoryWaypoint(
            timestamp_utc=step_time.isoformat(),
            t_seconds=t_sec,
            position_km=curr_r_sec_man,
            velocity_kmps=curr_v_sec_man,
            lat=round(lat_sm, 4),
            lng=round(lng_sm, 4),
            alt_km=round(alt_sm, 2),
        )

        steps.append(
            TrajectoryStep(
                timestamp_utc=step_time.isoformat(),
                t_seconds=t_sec,
                is_post_burn=burn_applied,
                nominal_primary=nom_pri_wp,
                nominal_secondary=nom_sec_wp,
                nominal_distance_km=round(d_nom, 3),
                maneuvered_primary=man_pri_wp,
                maneuvered_secondary=man_sec_wp,
                maneuvered_distance_km=round(d_man, 3),
            )
        )

        # Polylines in [lng, lat, alt_fraction] format matching react-globe.gl
        nominal_path_pri.append([round(lng_pn, 4), round(lat_pn, 4), round(alt_pn / EARTH_RADIUS_KM, 4)])
        nominal_path_sec.append([round(lng_sn, 4), round(lat_sn, 4), round(alt_sn / EARTH_RADIUS_KM, 4)])
        if primary_maneuvers:
            maneuvered_path.append([round(lng_pm, 4), round(lat_pm, 4), round(alt_pm / EARTH_RADIUS_KM, 4)])
        else:
            maneuvered_path.append([round(lng_sm, 4), round(lat_sm, 4), round(alt_sm / EARTH_RADIUS_KM, 4)])

        # Step forward
        curr_r_pri_nom, curr_v_pri_nom = rk4_step(curr_r_pri_nom, curr_v_pri_nom, float(step_seconds))
        curr_r_sec_nom, curr_v_sec_nom = rk4_step(curr_r_sec_nom, curr_v_sec_nom, float(step_seconds))
        curr_r_pri_man, curr_v_pri_man = rk4_step(curr_r_pri_man, curr_v_pri_man, float(step_seconds))
        curr_r_sec_man, curr_v_sec_man = rk4_step(curr_r_sec_man, curr_v_sec_man, float(step_seconds))

    cleared = min_dist_man >= CONJUNCTION_THRESHOLD_KM

    return ManeuverTrajectoryResult(
        conjunction_id=conjunction_id,
        primary_norad_id=primary.norad_id,
        primary_name=primary.name,
        secondary_norad_id=secondary.norad_id,
        secondary_name=secondary.name,
        maneuvering_norad_id=maneuvering_norad_id,
        maneuver_type=resolution.maneuver_type,
        delta_v_mps=resolution.delta_v_mps,
        execution_time_utc=resolution.execution_time_utc,
        tca_nominal_utc=tca_nom_time.isoformat(),
        min_distance_nominal_km=round(min_dist_nom, 3),
        tca_maneuvered_utc=tca_man_time.isoformat(),
        min_distance_maneuvered_km=round(min_dist_man, 3),
        cleared_threshold=cleared,
        steps=steps,
        nominal_path_primary=nominal_path_pri,
        nominal_path_secondary=nominal_path_sec,
        maneuvered_path=maneuvered_path,
    )


def simulate_seeded_conjunction_trajectory(
    delta_v_mps: float = 5.4,
    maneuver_type: str = "prograde_burn",
) -> ManeuverTrajectoryResult:
    """
    Convenience helper: Runs the maneuver trajectory engine against the
    locked A3 scenario (ISS 25544 <-> CSS 48274) with a verified maneuver resolution.
    With a burn 25 minutes prior to TCA, a 5.4 m/s impulsive prograde burn
    reliably widens the miss distance from 3.22 km to 12.7 km.
    """
    try:
        from backend.app.data.scenario import get_seeded_scenario_objects, SCENARIO_TCA_UTC
        from backend.app.schemas.negotiation import ResolutionStatus
    except ImportError:
        from app.data.scenario import get_seeded_scenario_objects, SCENARIO_TCA_UTC
        from app.schemas.negotiation import ResolutionStatus

    objects = get_seeded_scenario_objects(SCENARIO_TCA_UTC)
    primary = next(o for o in objects if o.norad_id == "25544")
    secondary = next(o for o in objects if o.norad_id == "48274")

    # Burn planned 25 minutes prior to TCA
    tca_dt = datetime.fromisoformat(SCENARIO_TCA_UTC.replace("Z", "+00:00")).astimezone(timezone.utc)
    burn_dt = tca_dt - timedelta(minutes=25)

    sample_resolution = Resolution(
        id="b6e4a1d2-9c3f-4e7a-8b2d-5f1a0c9e7d3b",
        conjunction_id="3f2a9c1e-7b4d-4a6f-9e0c-1d8b5a3f2e6c",
        maneuvering_agent="operator_A",
        maneuver_type=maneuver_type,
        delta_v_mps=delta_v_mps,
        execution_time_utc=burn_dt.isoformat(),
        expected_min_distance_km=12.7,
        residual_risk=0.0031,
        rationale_text="Operator A performed a 5.4 m/s prograde burn 25 min before TCA, widening miss distance to 12.7 km.",
        status=ResolutionStatus.APPROVED,
    )

    return generate_maneuver_trajectory(
        primary=primary,
        secondary=secondary,
        resolution=sample_resolution,
        window_minutes=60.0,
        step_seconds=30,
    )
