"""Literal geometry, timing and independent event checks for offline imports."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import math
from pathlib import Path
import tempfile
import unittest

from carla_import import ImportPolicy, import_export, load_export


ROOT = Path(__file__).resolve().parent
EXAMPLES = ROOT / "examples" / "carla"


def fixture(name="contact"):
    return json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))


def rotate(data, degrees):
    """Rotate the complete world and its chosen axis together about z."""
    radians = math.radians(degrees)
    cosine, sine = math.cos(radians), math.sin(radians)

    def vector(value):
        x, y, z = value
        return [cosine * x - sine * y, sine * x + cosine * y, z]

    data["axis"] = vector(data["axis"])
    for frame in data["frames"]:
        for actor in ("ego", "lead"):
            state = frame[actor]
            for key in ("location_m", "forward", "velocity_mps"):
                state[key] = vector(state[key])
            state["bbox_world_vertices_m"] = [vector(point) for point in state["bbox_world_vertices_m"]]
    return data


class ImportGeometryTests(unittest.TestCase):
    def test_literal_contact_geometry_origin_and_source_mapping(self):
        imported = load_export(EXAMPLES / "contact.json")
        self.assertEqual(imported.source_frame_ids, (100, 101, 102))
        self.assertEqual(imported.source_elapsed_seconds, (10.0, 11.0, 12.0))
        self.assertEqual(imported.time_origin_s, 10.0)
        self.assertEqual(imported.horizon_s, 2.0)
        self.assertEqual([sample.sample_id for sample in imported.samples], [0, 1, 2])
        self.assertEqual([sample.time_s for sample in imported.samples], [0.0, 1.0, 2.0])
        self.assertEqual([sample.ego_front_x_m for sample in imported.samples], [0.0, 10.0, 20.0])
        self.assertEqual([sample.lead_rear_x_m for sample in imported.samples], [10.0, 15.0, 20.0])
        self.assertEqual([sample.gap_m for sample in imported.samples], [10.0, 5.0, 0.0])
        self.assertEqual([sample.closing_speed_mps for sample in imported.samples], [5.0, 5.0, 5.0])
        self.assertEqual(imported.reference_contact_time_s, 2.0)

    def test_literal_opening_case_preserves_negative_closing_speed(self):
        imported = load_export(EXAMPLES / "noncontact.json")
        self.assertEqual([sample.gap_m for sample in imported.samples], [10.0, 15.0, 20.0])
        self.assertEqual([sample.closing_speed_mps for sample in imported.samples], [-5.0, -5.0, -5.0])
        self.assertIsNone(imported.reference_contact_time_s)

    def test_full_world_rotation_preserves_longitudinal_answers(self):
        for degrees in (45, 90, 180, -60):
            with self.subTest(degrees=degrees):
                imported = import_export(rotate(fixture(), degrees))
                for sample, expected in zip(imported.samples, (10, 5, 0)):
                    self.assertAlmostEqual(sample.gap_m, expected, places=10)
                    self.assertAlmostEqual(sample.closing_speed_mps, 5.0, places=12)

    def test_corner_order_does_not_change_front_and_rear(self):
        data = fixture()
        for frame in data["frames"]:
            for actor in ("ego", "lead"):
                frame[actor]["bbox_world_vertices_m"].reverse()
        self.assertEqual(import_export(data).samples, import_export(fixture()).samples)

    def test_heading_departure_rejected_at_each_actor_and_frame(self):
        for actor in ("ego", "lead"):
            data = fixture()
            data["frames"][1][actor]["forward"] = [math.cos(math.radians(6)), math.sin(math.radians(6)), 0]
            with self.subTest(actor=actor), self.assertRaisesRegex(ValueError, "heading"):
                import_export(data)

    def test_inclusive_heading_limit(self):
        data = fixture()
        data["frames"][1]["lead"]["forward"] = [math.cos(math.radians(5)), math.sin(math.radians(5)), 0]
        self.assertEqual(import_export(data).horizon_s, 2)

    def test_lateral_height_and_velocity_limits(self):
        cases = (("location_m", 1, 200.51, "lateral offset"),
                 ("location_m", 2, 1.51, "height offset"),
                 ("velocity_mps", 1, 0.51, "lateral speed"))
        for key, component, value, message in cases:
            with self.subTest(key=key, component=component):
                data = fixture()
                data["frames"][1]["lead"][key][component] = value
                with self.assertRaisesRegex(ValueError, message):
                    import_export(data)

    def test_inclusive_offset_limits_and_custom_policy(self):
        data = fixture()
        state = data["frames"][1]["lead"]
        state["location_m"][1] = 200.5
        state["location_m"][2] = 1.5
        state["velocity_mps"][1] = 0.5
        self.assertEqual(import_export(data).samples[1].gap_m, 5)
        with self.assertRaisesRegex(ValueError, "lateral offset"):
            import_export(data, ImportPolicy(max_lateral_offset_m=0.25))

    def test_reversing_is_not_converted_to_positive_speed(self):
        data = fixture()
        data["frames"][0]["ego"]["velocity_mps"][0] = -0.01
        with self.assertRaisesRegex(ValueError, "forward speed"):
            import_export(data)

    def test_degenerate_dimensions_rejected_with_distinct_vertices(self):
        for coordinate, message in ((0, "length"), (1, "width"), (2, "height")):
            with self.subTest(coordinate=coordinate):
                data = fixture()
                # Eight distinct coplanar points, with zero extent on one axis.
                varying = [index for index in range(3) if index != coordinate]
                points = []
                for first in (0, 1, 2, 3):
                    for second in (0, 1):
                        point = [0.0, 0.0, 0.0]
                        point[varying[0]] = float(first)
                        point[varying[1]] = float(second)
                        points.append(point)
                data["frames"][0]["ego"]["bbox_world_vertices_m"] = points
                with self.assertRaisesRegex(ValueError, f"degenerate projected {message}"):
                    import_export(data)


class ImportTimingAndEventTests(unittest.TestCase):
    def test_event_reference_is_independent_of_gap_zero(self):
        data = fixture()
        data["collisions"] = []
        imported = import_export(data)
        self.assertEqual(imported.samples[-1].gap_m, 0)
        self.assertIsNone(imported.reference_contact_time_s)

    def test_event_can_exist_with_positive_bounding_gap(self):
        data = fixture("noncontact")
        data["collisions"] = [{"frame": 102, "elapsed_seconds": 12.0, "actor_id": 1, "other_actor_id": 2}]
        imported = import_export(data)
        self.assertEqual(imported.samples[-1].gap_m, 20)
        self.assertEqual(imported.reference_contact_time_s, 2)

    def test_first_pair_event_and_other_actor_diagnostics(self):
        data = fixture()
        data["collisions"].extend([
            {"frame": 100, "elapsed_seconds": 10.0, "actor_id": 1, "other_actor_id": 99},
            {"frame": 101, "elapsed_seconds": 11.0, "actor_id": 1, "other_actor_id": 2},
            {"frame": 101, "elapsed_seconds": 11.0, "actor_id": 1, "other_actor_id": 2},
        ])
        imported = import_export(data)
        self.assertEqual(imported.reference_contact_time_s, 1)
        self.assertEqual(imported.ignored_collision_count, 1)

    def test_initial_and_horizon_events_inclusive(self):
        for frame, elapsed, expected in ((100, 10.0, 0), (102, 12.0, 2)):
            with self.subTest(frame=frame):
                data = fixture()
                data["collisions"] = [{"frame": frame, "elapsed_seconds": elapsed,
                                       "actor_id": 1, "other_actor_id": 2}]
                self.assertEqual(import_export(data).reference_contact_time_s, expected)

    def test_outside_event_not_rounded_inside_even_one_ulp(self):
        for frame, elapsed in ((100, math.nextafter(10.0, -math.inf)),
                               (102, math.nextafter(12.0, math.inf))):
            with self.subTest(frame=frame):
                data = fixture()
                data["collisions"] = [{"frame": frame, "elapsed_seconds": elapsed,
                                       "actor_id": 1, "other_actor_id": 2}]
                with self.assertRaisesRegex(ValueError, "outside captured"):
                    import_export(data)

    def test_bad_event_frame_time_or_sensor_parent(self):
        for field, value, message in (("frame", 999, "not captured"),
                                       ("elapsed_seconds", 11.5, "does not match"),
                                       ("actor_id", 2, "identify ego"),
                                       ("other_actor_id", 0, "integer")):
            with self.subTest(field=field):
                data = fixture()
                data["collisions"][0][field] = value
                with self.assertRaisesRegex(ValueError, message):
                    import_export(data)

    def test_strictly_increasing_source_ids_and_times(self):
        for field, value in (("frame", 100), ("frame", 99),
                             ("elapsed_seconds", 10), ("elapsed_seconds", 9)):
            with self.subTest(field=field, value=value):
                data = fixture()
                data["frames"][1][field] = value
                with self.assertRaisesRegex(ValueError, "strictly increase"):
                    import_export(data)

    def test_fixed_delta_uses_source_frame_increment(self):
        data = fixture()
        del data["frames"][1]
        imported = import_export(data)
        self.assertEqual(imported.source_frame_ids, (100, 102))
        self.assertEqual(imported.horizon_s, 2)

    def test_fixed_delta_mismatch_rejected(self):
        data = fixture()
        data["frames"][1]["elapsed_seconds"] = 10.5
        with self.assertRaisesRegex(ValueError, "fixed_delta_seconds"):
            import_export(data)

    def test_irregular_time_preserved_without_resampling(self):
        data = fixture()
        data["provenance"]["fixed_delta_seconds"] = None
        data["frames"][1]["elapsed_seconds"] = 10.25
        imported = import_export(data)
        self.assertEqual([sample.time_s for sample in imported.samples], [0, 0.25, 2])
        self.assertEqual(len(imported.samples), 3)
        self.assertEqual(imported.truth_at(0.125).gap_m, 7.5)

    def test_exact_knots_and_literal_midpoint_interpolation(self):
        imported = import_export(fixture())
        for sample in imported.samples:
            self.assertIs(imported.truth_at(sample.time_s), sample)
        midpoint = imported.truth_at(0.5)
        self.assertEqual(midpoint.ego_front_x_m, 5)
        self.assertEqual(midpoint.lead_rear_x_m, 12.5)
        self.assertEqual(midpoint.gap_m, 7.5)
        self.assertEqual(midpoint.closing_speed_mps, 5)
        self.assertEqual(midpoint.sample_id, 0)

    def test_interpolation_of_speeds_is_separate_from_positions(self):
        data = fixture()
        data["frames"][1]["ego"]["velocity_mps"][0] = 6
        data["frames"][1]["lead"]["velocity_mps"][0] = 1
        interpolated = import_export(data).truth_at(0.5)
        self.assertEqual(interpolated.ego_speed_mps, 8)
        self.assertEqual(interpolated.lead_speed_mps, 3)
        self.assertEqual(interpolated.closing_speed_mps, 5)

    def test_no_extrapolation_or_nonfinite_truth_queries(self):
        imported = import_export(fixture())
        for time_s in (-1e-12, math.nextafter(2.0, math.inf), math.inf, math.nan, True, "1"):
            with self.subTest(time_s=time_s), self.assertRaises(ValueError):
                imported.truth_at(time_s)

    def test_one_frame_zero_horizon(self):
        data = fixture()
        data["frames"] = data["frames"][:1]
        data["collisions"] = [{"frame": 100, "elapsed_seconds": 10.0,
                               "actor_id": 1, "other_actor_id": 2}]
        imported = import_export(data)
        self.assertEqual(imported.horizon_s, 0)
        self.assertEqual(imported.reference_contact_time_s, 0)
        self.assertIs(imported.truth_at(0), imported.samples[0])
        with self.assertRaises(ValueError):
            imported.truth_at(1e-12)


class ImportValidationTests(unittest.TestCase):
    def test_input_is_unchanged_and_provenance_is_copied(self):
        data = fixture()
        before = deepcopy(data)
        imported = import_export(data)
        self.assertEqual(data, before)
        data["provenance"]["capture_id"] = "changed"
        self.assertEqual(imported.provenance["capture_id"], "synthetic_contact_001")
        self.assertEqual(imported.provenance["kind"], "synthetic-contract-fixture")
        self.assertTrue(any("not an actual CARLA" in warning for warning in imported.warnings))
        self.assertTrue(any("piecewise-linear" in warning for warning in imported.warnings))
        with self.assertRaises(FrozenInstanceError):
            imported.scenario_id = "changed"

    def test_declared_simulator_provenance_does_not_claim_authentication(self):
        data = fixture()
        data["provenance"]["kind"] = "carla-simulator"
        imported = import_export(data)
        self.assertTrue(any("does not certify" in warning for warning in imported.warnings))

    def test_incomplete_or_nonboolean_collision_coverage_rejected(self):
        for value in (False, None, 1, "true"):
            with self.subTest(value=value):
                data = fixture()
                data["provenance"]["collision_sensor_complete"] = value
                with self.assertRaisesRegex(ValueError, "collision_sensor_complete"):
                    import_export(data)

    def test_unknown_and_missing_keys_at_all_object_levels(self):
        paths = ((), ("provenance",), ("units",), ("actors",),
                 ("frames", 0), ("frames", 0, "ego"), ("collisions", 0))
        for path in paths:
            for operation in ("unknown", "missing"):
                with self.subTest(path=path, operation=operation):
                    data = fixture()
                    target = data
                    for part in path:
                        target = target[part]
                    if operation == "unknown":
                        target["unexpected"] = 1
                    else:
                        del target[next(iter(target))]
                    with self.assertRaisesRegex(ValueError, "exactly these keys"):
                        import_export(data)

    def test_units_and_safe_scenario_identity(self):
        for scenario_id in ("", "bad/path", "Upper", "manifest", "con", "com1", "lpt9"):
            with self.subTest(scenario_id=scenario_id):
                data = fixture()
                data["scenario_id"] = scenario_id
                with self.assertRaises(ValueError):
                    import_export(data)
        data = fixture()
        data["units"]["position"] = "cm"
        with self.assertRaisesRegex(ValueError, "units"):
            import_export(data)

    def test_nonunit_nonhorizontal_and_malformed_vectors(self):
        for value in ([2, 0, 0], [0, 0, 1], [1, 0], "1,0,0", [True, 0, 0], [math.inf, 0, 0]):
            with self.subTest(value=value):
                data = fixture()
                data["axis"] = value
                with self.assertRaises(ValueError):
                    import_export(data)
        data = fixture()
        data["frames"][0]["lead"]["forward"] = [0.99, 0, 0]
        with self.assertRaisesRegex(ValueError, "unit vector"):
            import_export(data)

    def test_malformed_frames_actors_boxes_and_provenance(self):
        cases = (("frames", []), ("frames", {}), ("collisions", {}),
                 ("actors", {"ego": 1, "lead": 1}),
                 ("actors", {"ego": True, "lead": 2}),
                 ("provenance", None))
        for field, value in cases:
            with self.subTest(field=field, value=value):
                data = fixture()
                data[field] = value
                with self.assertRaises(ValueError):
                    import_export(data)
        for value in ([], [[0, 0, 0]] * 8, [[0, 0]] * 8, "box"):
            with self.subTest(value=value):
                data = fixture()
                data["frames"][0]["ego"]["bbox_world_vertices_m"] = value
                with self.assertRaises(ValueError):
                    import_export(data)

    def test_bool_and_nonfinite_numbers_rejected_inside_records(self):
        paths = (("frames", 0, "frame"), ("frames", 0, "elapsed_seconds"),
                 ("frames", 0, "ego", "location_m", 0),
                 ("frames", 0, "lead", "velocity_mps", 0),
                 ("frames", 0, "ego", "bbox_world_vertices_m", 0, 0),
                 ("provenance", "fixed_delta_seconds"))
        for path in paths:
            for value in (True, math.nan, math.inf, "10", 10 ** 1000):
                with self.subTest(path=path, value=repr(value)[:35]):
                    data = fixture()
                    target = data
                    for part in path[:-1]:
                        target = target[part]
                    target[path[-1]] = value
                    with self.assertRaises(ValueError):
                        import_export(data)

    def test_policy_rejects_invalid_limits_and_types(self):
        for field in ("max_heading_error_deg", "max_lateral_offset_m",
                      "max_lateral_speed_mps", "max_height_offset_m"):
            for value in (0, -1, True, math.inf, math.nan, "5"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    ImportPolicy(**{field: value})
        with self.assertRaises(ValueError):
            ImportPolicy(max_heading_error_deg=90)
        with self.assertRaises(ValueError):
            import_export(fixture(), policy={})

    def test_derived_projection_extent_and_origin_overflow(self):
        for case in ("extent", "origin", "velocity"):
            with self.subTest(case=case):
                data = fixture()
                if case == "velocity":
                    data = rotate(data, 45)
                    data["frames"][0]["ego"]["velocity_mps"] = [1.79e308, 1.79e308, 0]
                else:
                    ego_xs = (-1e308, 1e308) if case == "extent" else (-1e308, -0.9e308)
                    data["frames"][0]["ego"]["bbox_world_vertices_m"] = [
                        [x, y, z] for x in ego_xs for y in (199, 201) for z in (0, 2)]
                    if case == "origin":
                        data["frames"][0]["lead"]["bbox_world_vertices_m"] = [
                            [x, y, z] for x in (0.9e308, 1e308) for y in (199, 201) for z in (0, 2)]
                with self.assertRaisesRegex(ValueError, "finite"):
                    import_export(data)

    def test_fixed_delta_frame_multiplication_overflow(self):
        data = fixture()
        data["frames"][1]["frame"] = 10 ** 1000
        with self.assertRaisesRegex(ValueError, "finite arithmetic"):
            import_export(data)

    def test_json_duplicate_keys_nonfinite_overflow_and_encoding(self):
        serialized = json.dumps(fixture())
        bad_json = (
            serialized.replace('"schema_version":', '"schema_version": "duplicate", "schema_version":', 1),
            serialized.replace('"kind":', '"kind": "duplicate", "kind":', 1),
            serialized.replace('"fixed_delta_seconds": 1.0', '"fixed_delta_seconds": NaN'),
            serialized.replace('"fixed_delta_seconds": 1.0', '"fixed_delta_seconds": Infinity'),
            serialized.replace('"fixed_delta_seconds": 1.0', '"fixed_delta_seconds": 1e309'),
            "{bad json}",
        )
        output_root = ROOT / "outputs"
        output_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output_root) as directory:
            path = Path(directory) / "export.json"
            for text in bad_json:
                with self.subTest(text=text[:60]):
                    path.write_text(text, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_export(path)
            path.write_bytes(b"\xff")
            with self.assertRaisesRegex(ValueError, "invalid export JSON"):
                load_export(path)

    def test_load_does_not_change_source_bytes(self):
        path = EXAMPLES / "contact.json"
        original = path.read_bytes()
        load_export(path)
        self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
