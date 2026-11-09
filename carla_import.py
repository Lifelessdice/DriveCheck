"""Strict offline import of a custom CARLA-state export; no simulator dependency."""

from bisect import bisect_left
from copy import deepcopy
from dataclasses import dataclass
import json
import math
from pathlib import Path

from motion import Scenario, TruthSample, require_finite


SCHEMA = "drivecheck.carla-export.v1"
UNIT_TOLERANCE = 1e-9
TIME_ABSOLUTE_TOLERANCE_S = 1e-9
TIME_RELATIVE_TOLERANCE = 1e-9
MINIMUM_PROJECTED_EXTENT_M = 1e-9


def _number(name, value, *, minimum=None, positive=False):
    require_finite(name, value, minimum=minimum, positive=positive)
    return float(value)


def _integer(name, value, *, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _keys(value, expected, name):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f"{name} must have exactly these keys: {', '.join(sorted(expected))}")


def _text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")
    return value


def _vector(name, value, *, unit=False):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{name} must be a 3-vector JSON array")
    result = tuple(_number(f"{name}[{index}]", component)
                   for index, component in enumerate(value))
    if unit and not math.isclose(math.hypot(*result), 1.0,
                                 rel_tol=0, abs_tol=UNIT_TOLERANCE):
        raise ValueError(f"{name} must be a unit vector")
    return result


def _sum(name, values):
    try:
        result = math.fsum(values)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} exceeds finite arithmetic") from error
    return _number(name, result)


def _dot(name, vector, axis):
    products = [_number(name, value * direction)
                for value, direction in zip(vector, axis)]
    return _sum(name, products)


@dataclass(frozen=True)
class ImportPolicy:
    """Maximum departures from a fixed horizontal longitudinal projection."""

    max_heading_error_deg: float = 5.0
    max_lateral_offset_m: float = 0.5
    max_lateral_speed_mps: float = 0.5
    max_height_offset_m: float = 0.5

    def __post_init__(self):
        for name in ("max_heading_error_deg", "max_lateral_offset_m",
                     "max_lateral_speed_mps", "max_height_offset_m"):
            _number(name, getattr(self, name), positive=True)
        if self.max_heading_error_deg >= 90:
            raise ValueError("max_heading_error_deg must be < 90")


@dataclass(frozen=True)
class ImportedTrajectory:
    """Recorded knots and an explicitly approximate offline truth callback."""

    scenario_id: str
    samples: tuple[TruthSample, ...]
    source_frame_ids: tuple[int, ...]
    source_elapsed_seconds: tuple[float, ...]
    reference_contact_time_s: float | None
    provenance: dict
    ignored_collision_count: int
    warnings: tuple[str, ...]
    time_origin_s: float
    mapping_policy: ImportPolicy

    @property
    def horizon_s(self):
        return self.samples[-1].time_s

    def truth_at(self, time_s):
        """Return stored knots or linear state interpolation; never extrapolate.

        An interpolated record keeps the left knot's sample ID. Position and
        speed are interpolated separately; this is not continuous CARLA physics.
        """
        time_s = _number("truth query time_s", time_s, minimum=0)
        if time_s > self.horizon_s:
            raise ValueError("truth query time_s exceeds captured horizon")
        index = bisect_left(self.samples, time_s, key=lambda sample: sample.time_s)
        if self.samples[index].time_s == time_s:
            return self.samples[index]
        left, right = self.samples[index - 1], self.samples[index]
        fraction = (time_s - left.time_s) / (right.time_s - left.time_s)

        def interpolate(field):
            # A convex sum avoids overflow from subtracting opposite endpoints.
            return _sum(field, ((1.0 - fraction) * getattr(left, field),
                                fraction * getattr(right, field)))

        ego_x = interpolate("ego_front_x_m")
        lead_x = interpolate("lead_rear_x_m")
        ego_speed = interpolate("ego_speed_mps")
        lead_speed = interpolate("lead_speed_mps")
        return TruthSample(
            scenario_id=self.scenario_id, sample_id=left.sample_id, time_s=time_s,
            ego_front_x_m=ego_x, lead_rear_x_m=lead_x,
            ego_speed_mps=ego_speed, lead_speed_mps=lead_speed,
            gap_m=_number("interpolated gap_m", lead_x - ego_x),
            closing_speed_mps=_number("interpolated closing_speed_mps", ego_speed - lead_speed),
        )


def _provenance(value):
    _keys(value, {"kind", "carla_version", "map_name", "capture_id",
                  "fixed_delta_seconds", "collision_sensor_complete"}, "provenance")
    if value["kind"] not in ("synthetic-contract-fixture", "carla-simulator"):
        raise ValueError("provenance.kind must declare synthetic-contract-fixture or carla-simulator")
    for name in ("carla_version", "map_name", "capture_id"):
        _text(f"provenance.{name}", value[name])
    if value["fixed_delta_seconds"] is not None:
        _number("provenance.fixed_delta_seconds", value["fixed_delta_seconds"], positive=True)
    if value["collision_sensor_complete"] is not True:
        raise ValueError("provenance.collision_sensor_complete must be true")
    return deepcopy(value)


def _actor(state, name, axis, lateral, reference_lateral, reference_height, policy):
    _keys(state, {"location_m", "forward", "velocity_mps", "bbox_world_vertices_m"}, name)
    location = _vector(f"{name}.location_m", state["location_m"])
    forward = _vector(f"{name}.forward", state["forward"], unit=True)
    velocity = _vector(f"{name}.velocity_mps", state["velocity_mps"])
    cosine = _dot(f"{name} heading", forward, axis)
    heading_deg = math.degrees(math.acos(max(-1.0, min(1.0, cosine))))
    if heading_deg > policy.max_heading_error_deg + UNIT_TOLERANCE:
        raise ValueError(f"{name} heading exceeds max_heading_error_deg")
    lateral_position = _dot(f"{name} lateral position", location, lateral)
    lateral_offset = _number(f"{name} lateral offset", lateral_position - reference_lateral)
    height_offset = _number(f"{name} height offset", location[2] - reference_height)
    if abs(lateral_offset) > policy.max_lateral_offset_m:
        raise ValueError(f"{name} lateral offset exceeds max_lateral_offset_m")
    if abs(height_offset) > policy.max_height_offset_m:
        raise ValueError(f"{name} height offset exceeds max_height_offset_m")
    lateral_speed = _dot(f"{name} lateral speed", velocity, lateral)
    if abs(lateral_speed) > policy.max_lateral_speed_mps:
        raise ValueError(f"{name} lateral speed exceeds max_lateral_speed_mps")
    speed = _dot(f"{name} forward speed", velocity, axis)
    if speed < 0:
        raise ValueError(f"{name} projected forward speed must be >= 0")
    vertices = state["bbox_world_vertices_m"]
    if not isinstance(vertices, list) or len(vertices) != 8:
        raise ValueError(f"{name}.bbox_world_vertices_m must contain eight vertices")
    corners = tuple(_vector(f"{name}.bbox_world_vertices_m[{index}]", vertex)
                    for index, vertex in enumerate(vertices))
    if len(set(corners)) != 8:
        raise ValueError(f"{name}.bbox_world_vertices_m must contain eight distinct vertices")
    projections = []
    for label, direction in (("length", axis), ("width", lateral), ("height", (0.0, 0.0, 1.0))):
        values = [_dot(f"{name} {label} projection", corner, direction) for corner in corners]
        extent = _number(f"{name} projected {label}", max(values) - min(values))
        if extent <= MINIMUM_PROJECTED_EXTENT_M:
            raise ValueError(f"{name} has degenerate projected {label}")
        projections.append(values)
    return max(projections[0]), min(projections[0]), speed


def import_export(data, policy=None):
    """Validate a custom export and map frame states without changing the input."""
    policy = ImportPolicy() if policy is None else policy
    if not isinstance(policy, ImportPolicy):
        raise ValueError("policy must be an ImportPolicy or None")
    _keys(data, {"schema_version", "scenario_id", "provenance", "units", "axis",
                 "actors", "frames", "collisions"}, "export")
    if data["schema_version"] != SCHEMA:
        raise ValueError(f"schema_version must be {SCHEMA}")
    scenario_id = _text("scenario_id", data["scenario_id"])
    # Reuse the core's portable scenario-ID and reserved-filename checks.
    Scenario(scenario_id, 0.0, 0.0, 0.0, 1.0, 1)
    _keys(data["units"], {"position", "velocity", "time"}, "units")
    if data["units"] != {"position": "m", "velocity": "m/s", "time": "s"}:
        raise ValueError("units must declare position=m, velocity=m/s, time=s")
    axis = _vector("axis", data["axis"], unit=True)
    if abs(axis[2]) > UNIT_TOLERANCE:
        raise ValueError("axis must be horizontal")
    lateral = (-axis[1], axis[0], 0.0)
    _keys(data["actors"], {"ego", "lead"}, "actors")
    ego_id = _integer("actors.ego", data["actors"]["ego"], minimum=1)
    lead_id = _integer("actors.lead", data["actors"]["lead"], minimum=1)
    if ego_id == lead_id:
        raise ValueError("actors.ego and actors.lead must be distinct")
    provenance = _provenance(data["provenance"])
    frames = data["frames"]
    if not isinstance(frames, list) or not frames:
        raise ValueError("frames must be a nonempty JSON array")
    if not isinstance(data["collisions"], list):
        raise ValueError("collisions must be a JSON array")

    samples, source_ids, source_times = [], [], []
    origin = reference_lateral = reference_height = time_origin = None
    delta = provenance["fixed_delta_seconds"]
    for sample_id, frame in enumerate(frames):
        label = f"frames[{sample_id}]"
        _keys(frame, {"frame", "elapsed_seconds", "ego", "lead"}, label)
        frame_id = _integer(f"{label}.frame", frame["frame"])
        world_time = _number(f"{label}.elapsed_seconds", frame["elapsed_seconds"], minimum=0)
        if source_ids:
            if frame_id <= source_ids[-1] or world_time <= source_times[-1]:
                raise ValueError(f"{label}: frame IDs and elapsed_seconds must strictly increase")
            interval = _number(f"{label} elapsed interval", world_time - source_times[-1])
            if delta is not None:
                try:
                    expected = _number(f"{label} expected interval", delta * (frame_id - source_ids[-1]))
                except OverflowError as error:
                    raise ValueError(f"{label}: fixed-delta interval exceeds finite arithmetic") from error
                if not math.isclose(interval, expected, rel_tol=TIME_RELATIVE_TOLERANCE,
                                    abs_tol=TIME_ABSOLUTE_TOLERANCE_S):
                    raise ValueError(f"{label}: elapsed/frame increment disagrees with fixed_delta_seconds")
        if time_origin is None:
            _keys(frame["ego"], {"location_m", "forward", "velocity_mps", "bbox_world_vertices_m"}, f"{label}.ego")
            first_location = _vector(f"{label}.ego.location_m", frame["ego"]["location_m"])
            reference_lateral = _dot("initial ego lateral position", first_location, lateral)
            reference_height = first_location[2]
            time_origin = world_time
        ego_front, _, ego_speed = _actor(frame["ego"], f"{label}.ego", axis, lateral,
                                         reference_lateral, reference_height, policy)
        _, lead_rear, lead_speed = _actor(frame["lead"], f"{label}.lead", axis, lateral,
                                         reference_lateral, reference_height, policy)
        if origin is None:
            origin = ego_front
        ego_x = _number(f"{label} normalized ego position", ego_front - origin)
        lead_x = _number(f"{label} normalized lead position", lead_rear - origin)
        time_s = _number(f"{label} normalized time", world_time - time_origin, minimum=0)
        if samples and time_s <= samples[-1].time_s:
            raise ValueError(f"{label}: normalized times must strictly increase")
        samples.append(TruthSample(
            scenario_id, sample_id, time_s, ego_x, lead_x, ego_speed, lead_speed,
            _number(f"{label} gap_m", lead_x - ego_x),
            _number(f"{label} closing_speed_mps", ego_speed - lead_speed),
        ))
        source_ids.append(frame_id)
        source_times.append(world_time)

    frame_times = dict(zip(source_ids, source_times))
    event_times, ignored = [], 0
    for index, event in enumerate(data["collisions"]):
        label = f"collisions[{index}]"
        _keys(event, {"frame", "elapsed_seconds", "actor_id", "other_actor_id"}, label)
        event_frame = _integer(f"{label}.frame", event["frame"])
        event_time = _number(f"{label}.elapsed_seconds", event["elapsed_seconds"], minimum=0)
        if event_time < source_times[0] or event_time > source_times[-1]:
            raise ValueError(f"{label}: event lies outside captured time bounds")
        if event_frame not in frame_times:
            raise ValueError(f"{label}: event frame is not captured")
        if not math.isclose(event_time, frame_times[event_frame], rel_tol=0,
                            abs_tol=TIME_ABSOLUTE_TOLERANCE_S):
            raise ValueError(f"{label}: timestamp does not match its captured frame")
        if _integer(f"{label}.actor_id", event["actor_id"], minimum=1) != ego_id:
            raise ValueError(f"{label}.actor_id must identify ego")
        other_id = _integer(f"{label}.other_actor_id", event["other_actor_id"], minimum=1)
        if other_id == lead_id:
            # Keep the declared event time; never round an outside event inward.
            event_times.append(_number(f"{label} normalized time", event_time - time_origin, minimum=0))
        else:
            ignored += 1

    warnings = [
        "Custom DriveCheck export contract; not an official CARLA log format.",
        "Provenance is a declaration and does not certify capture authenticity.",
        "Bounding-box projections approximate bumper positions; collision events are independent of gap/TTC.",
        "Offline truth uses piecewise-linear positions/speeds between knots, not exact continuous simulator physics.",
    ]
    if provenance["kind"] == "synthetic-contract-fixture":
        warnings.append("Synthetic contract fixture; not an actual CARLA simulator capture.")
    if delta is None:
        warnings.append("Irregular source times are allowed and preserved without resampling.")
    if len(samples) == 1:
        warnings.append("One captured frame: sub-frame collision timing resolution is unavailable.")
    else:
        maximum_interval = max(b.time_s - a.time_s for a, b in zip(samples, samples[1:]))
        warnings.append(f"Maximum recorded frame interval is {maximum_interval:g} s; sub-frame collision timing is unverified.")
    return ImportedTrajectory(
        scenario_id=scenario_id, samples=tuple(samples), source_frame_ids=tuple(source_ids),
        source_elapsed_seconds=tuple(source_times),
        reference_contact_time_s=min(event_times) if event_times else None,
        provenance=provenance, ignored_collision_count=ignored, warnings=tuple(warnings),
        time_origin_s=time_origin, mapping_policy=policy,
    )


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_constant(value):
    raise ValueError(f"non-finite JSON constant: {value}")


def _json_float(value):
    return _number("JSON number", float(value))


def parse_export(content, policy=None):
    """Import the exact UTF-8 JSON bytes provided by the caller."""
    try:
        data = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=_reject_constant, parse_float=_json_float)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid export JSON: {error}") from error
    return import_export(data, policy=policy)


def load_export(path, policy=None):
    """Read a UTF-8 JSON export from disk and validate it."""
    return parse_export(Path(path).read_bytes(), policy=policy)
