"""Independent event-scoring fixtures and summary-denominator checks."""

import unittest
from copy import deepcopy

from evaluation import score_case, summarize
from motion import sample_truth
from observations import make_observations
from replay import make_decision_times, replay
from scenarios import m1_fixtures
from warning_policy import Decision


def decision_rows(rows):
    """Construct metric fixtures without invoking the warning policy."""

    return [
        Decision(
            decision_time_s=time_s,
            is_warning=warning,
            reason="scoring_fixture",
        )
        for time_s, warning in rows
    ]


def literal_case(
    case_id,
    outcome=None,
    *,
    condition_id="clean",
    status="complete",
    positive=None,
):
    """Build independently specified summary inputs."""

    if positive is None:
        positive = outcome in ("useful", "late", "missed")

    reference = 5.0 if positive else None

    matched_time, lead = {
        "useful": (3.0, 2.0),
        "late": (4.5, 0.5),
    }.get(outcome, (None, None))

    score = None

    if status == "complete":
        score = {
            "outcome": outcome,
            "reference_contact_time_s": reference,
            "horizon_s": 8.0,
            "pre_event_window_s": 4.0,
            "minimum_useful_lead_s": 1.0,
            "first_matched_warning_time_s": matched_time,
            "matched_lead_s": lead,
        }

    return {
        "case_id": case_id,
        "condition_id": condition_id,
        "status": status,
        "reference_contact_time_s": reference,
        "horizon_s": 8.0,
        "score": score,
    }


class EventScoringTests(unittest.TestCase):
    """Check matching conventions using literal decision times and flags."""

    def test_literal_matching_fixtures(self):
        """Use event 5 s, window [1,5] s and useful lead at least 1 s."""
        # Time 4 is exactly useful; time 5 is matched but late with zero lead.
        cases = [
            ([], "missed", None),
            ([0.5], "missed", None),
            ([0.999999], "missed", None),
            ([1.0], "useful", 4.0),
            ([1.0, 4.5], "useful", 4.0),
            ([4.0], "useful", 1.0),
            ([4.25], "late", 0.75),
            ([5.0], "late", 0.0),
            ([5.000001], "missed", None),
            ([0.5, 2.0, 3.0], "useful", 3.0),
        ]

        for times, outcome, lead in cases:
            with self.subTest(times=times):
                result = score_case(
                    decision_rows([(time_s, True) for time_s in times]),
                    5.0,
                    8.0,
                )

                self.assertEqual(result["outcome"], outcome)

                if lead is None:
                    self.assertIsNone(result["matched_lead_s"])
                else:
                    self.assertAlmostEqual(result["matched_lead_s"], lead)

        # An early activation can qualify through its later in-window decision.
        result = score_case(
            decision_rows([(0.5, True), (2.0, True), (3.0, True)]),
            5.0,
            8.0,
        )

        self.assertEqual(result["first_warning_time_s"], 0.5)
        self.assertEqual(result["first_matched_warning_time_s"], 2.0)
        self.assertEqual(result["early_warning_decision_count"], 1)
        self.assertEqual(result["warning_activation_count"], 1)

        post_contact = score_case(
            decision_rows([(5.01, True)]),
            5.0,
            8.0,
        )
        self.assertEqual(
            post_contact["post_contact_warning_decision_count"],
            1,
        )

    def test_activations_and_negative_episodes(self):
        """Three true rows form two activations and one episode outcome."""
        decisions = decision_rows(
            [
                (1.0, True),
                (2.0, True),
                (3.0, False),
                (4.0, True),
            ]
        )

        positive = score_case(decisions, 5.0, 8.0)
        negative = score_case(decisions, None, 8.0)

        self.assertEqual(positive["warning_decision_count"], 3)
        self.assertEqual(positive["warning_activation_count"], 2)
        self.assertEqual(positive["outcome"], "useful")

        self.assertEqual(negative["outcome"], "false_warning")
        self.assertIsNone(negative["matched_lead_s"])
        self.assertEqual(negative["warning_activation_count"], 2)

        clear = score_case(
            decision_rows([(0.0, False), (1.0, False)]),
            None,
            8.0,
        )
        self.assertEqual(clear["outcome"], "clear_negative")

    def test_initial_and_horizon_contact(self):
        """Contacts at both inclusive endpoints remain positive episodes."""
        initial = score_case(
            decision_rows([(0.0, True)]),
            0.0,
            0.0,
        )
        final = score_case(
            decision_rows([(8.0, True)]),
            8.0,
            8.0,
        )

        for result in (initial, final):
            self.assertEqual(result["outcome"], "late")
            self.assertEqual(result["matched_lead_s"], 0.0)

    def test_invalid_reference_and_policy(self):
        """Reject invalid event bounds and inconsistent scoring settings."""
        changes = [
            {"reference_contact_time_s": -1},
            {"reference_contact_time_s": True},
            {"reference_contact_time_s": float("nan")},
            {"reference_contact_time_s": 8.001},
            {"horizon_s": -1},
            {"horizon_s": True},
            {"pre_event_window_s": 0},
            {"minimum_useful_lead_s": 0},
            {"minimum_useful_lead_s": 5},
        ]

        for change in changes:
            settings = {
                "reference_contact_time_s": 5.0,
                "horizon_s": 8.0,
            }
            settings.update(change)

            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    score_case([], **settings)

    def test_invalid_decisions(self):
        """Require ordered finite timestamps and exact boolean warning flags."""
        invalid = [
            [{}],
            decision_rows([(1.0, True), (1.0, False)]),
            decision_rows([(2.0, True), (1.0, True)]),
            decision_rows([(-1.0, True)]),
            decision_rows([(9.0, True)]),
            decision_rows([(float("nan"), True)]),
            decision_rows([(float("inf"), True)]),
            decision_rows([(True, True)]),
            decision_rows([(1.0, 1)]),
        ]

        for decisions in invalid:
            with self.subTest(decisions=decisions):
                with self.assertRaises(ValueError):
                    score_case(decisions, 5.0, 8.0)

    def test_empty_decisions(self):
        """No warning decisions yields missed contact or clear negative."""
        positive = score_case([], 5.0, 8.0)
        negative = score_case([], None, 8.0)

        self.assertEqual(positive["outcome"], "missed")
        self.assertIsNone(positive["matched_lead_s"])
        self.assertEqual(negative["outcome"], "clear_negative")


class SummaryTests(unittest.TestCase):
    """Keep eligible denominators independent of unsuccessful executions."""

    def test_literal_summary_with_unscored_cases(self):
        """Seven planned cases contain five completed and two unscored cases."""
        rows = [
            literal_case("useful", "useful"),
            literal_case("late", "late"),
            literal_case("missed", "missed"),
            literal_case("false", "false_warning"),
            literal_case("clear", "clear_negative"),
            literal_case(
                "failed-positive",
                status="failed",
                positive=True,
            ),
            literal_case(
                "partial-negative",
                status="partial",
                positive=False,
            ),
        ]

        result = summarize(rows)[0]

        # The failed positive and partial negative stay in planned counts.
        self.assertEqual(result["planned"], {"positive": 4, "negative": 3})
        self.assertEqual(result["scored"], {"positive": 3, "negative": 2})
        self.assertEqual(result["unscored"], {"positive": 1, "negative": 1})
        self.assertEqual(result["status_counts"]["complete"], 5)
        self.assertEqual(result["status_counts"]["failed"], 1)
        self.assertEqual(result["status_counts"]["partial"], 1)

        missed = result["rates"]["missed"]
        self.assertEqual(missed["numerator"], 1)
        self.assertEqual(missed["denominator"], 3)
        self.assertAlmostEqual(missed["value"], 1 / 3)

        self.assertAlmostEqual(
            result["rates"]["without_useful_warning"]["value"],
            2 / 3,
        )
        self.assertEqual(
            result["rates"]["false_warning_episode"],
            {"numerator": 1, "denominator": 2, "value": 0.5},
        )
        self.assertEqual(
            result["unscored_case_ids"],
            ["failed-positive", "partial-negative"],
        )

    def test_zero_denominator_conditions(self):
        """Absent eligible labels produce null rates rather than zero."""
        self.assertEqual(summarize([]), [])

        rows = [
            literal_case("p", "useful", condition_id="positive_only"),
            literal_case(
                "n",
                "clear_negative",
                condition_id="negative_only",
            ),
            literal_case(
                "failed",
                condition_id="failed_only",
                status="failed",
                positive=True,
            ),
        ]

        groups = {group["condition_id"]: group for group in summarize(rows)}

        self.assertIsNone(
            groups["positive_only"]["rates"]["false_warning_episode"]["value"]
        )
        self.assertIsNone(groups["negative_only"]["rates"]["missed"]["value"])
        self.assertEqual(
            groups["failed_only"]["rates"]["missed"],
            {"numerator": 0, "denominator": 0, "value": None},
        )

    def test_rejects_inconsistent_complete_results(self):
        """Contradictory completed scores must fail instead of being omitted."""
        valid = literal_case("case", "useful")

        changes = [
            {"outcome": "clear_negative"},
            {"reference_contact_time_s": 4.0},
            {"matched_lead_s": 20.0},
            {"first_matched_warning_time_s": 6.0},
            {
                "first_matched_warning_time_s": 4.5,
                "matched_lead_s": 0.5,
            },
            {"pre_event_window_s": 0},
        ]

        for change in changes:
            broken = deepcopy(valid)
            broken["score"].update(change)

            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    summarize([broken])

        broken = deepcopy(valid)
        broken["score"] = None

        with self.assertRaises(ValueError):
            summarize([broken])

    def test_rejects_duplicate_or_invalid_case_metadata(self):
        """Reject double-counted identities and invalid case labels/statuses."""
        valid = literal_case("case", "useful")

        with self.assertRaises(ValueError):
            summarize([valid, deepcopy(valid)])

        for change in (
            {"status": "unknown"},
            {"condition_id": ""},
            {"horizon_s": True},
            {"reference_contact_time_s": 8.001},
        ):
            broken = deepcopy(valid)
            broken.update(change)

            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    summarize([broken])

        with self.assertRaises(ValueError):
            summarize([{}])

    def test_does_not_mutate_input_rows(self):
        """Aggregation leaves the detailed input evidence unchanged."""
        rows = [
            literal_case("useful", "useful"),
            literal_case("failed", status="failed", positive=True),
        ]
        before = deepcopy(rows)

        summarize(rows)

        self.assertEqual(rows, before)


class ScoringIntegrationTests(unittest.TestCase):
    """Connect real replay output to the independent M1 event fixtures."""

    def test_scores_six_m1_cases(self):
        """Check all three unchanged trajectories under two delivery settings."""
        # Contact at sqrt(11) gives the fixed leads after warnings at 2/3 s.
        # Negative fixtures can warn about eventual contact beyond their H.
        expected = {
            ("constant_speed_original", "clean"): ("false_warning", 3.0, None),
            ("constant_speed_original", "latency_1s"): ("false_warning", 4.0, None),
            ("lead_braking_contact", "clean"): ("useful", 2.0, 1.3166247903554),
            ("lead_braking_contact", "latency_1s"): ("late", 3.0, 0.3166247903554),
            ("lead_braking_noncontact", "clean"): ("false_warning", 7.0, None),
            ("lead_braking_noncontact", "latency_1s"): ("false_warning", 8.0, None),
        }

        rows = []

        for fixture in m1_fixtures():
            scenario = fixture.scenario
            truth = sample_truth(scenario)
            base_times = [
                index * scenario.timestep_s for index in range(scenario.sample_count)
            ]

            for condition, delay_s in (
                ("clean", 0.0),
                ("latency_1s", 1.0),
            ):
                readings = make_observations(truth, delay_s)

                times = make_decision_times(
                    base_times,
                    readings,
                    scenario.horizon_s,
                    scenario_id=scenario.scenario_id,
                )
                result = replay(
                    readings,
                    times,
                    scenario_id=scenario.scenario_id,
                    horizon_s=scenario.horizon_s,
                )
                score = score_case(
                    result.decisions,
                    fixture.reference_contact_time_s,
                    scenario.horizon_s,
                )

                outcome, first_warning, lead = expected[
                    (scenario.scenario_id, condition)
                ]

                self.assertEqual(score["outcome"], outcome)
                self.assertEqual(
                    score["first_warning_time_s"],
                    first_warning,
                )

                if lead is None:
                    self.assertIsNone(score["matched_lead_s"])
                else:
                    self.assertAlmostEqual(
                        score["matched_lead_s"],
                        lead,
                        delta=1e-9,
                    )

                rows.append(
                    {
                        "case_id": f"{scenario.scenario_id}__{condition}",
                        "condition_id": condition,
                        "status": "complete",
                        "reference_contact_time_s": fixture.reference_contact_time_s,
                        "horizon_s": scenario.horizon_s,
                        "score": score,
                    }
                )

        groups = {group["condition_id"]: group for group in summarize(rows)}

        self.assertEqual(len(rows), 6)
        self.assertEqual(groups["clean"]["outcomes"]["useful"], 1)
        self.assertEqual(groups["latency_1s"]["outcomes"]["late"], 1)

        for group in groups.values():
            self.assertEqual(
                group["scored"],
                {"positive": 1, "negative": 2},
            )
            self.assertEqual(group["outcomes"]["missed"], 0)
            self.assertEqual(
                group["rates"]["false_warning_episode"]["value"],
                1.0,
            )


if __name__ == "__main__":
    unittest.main()
