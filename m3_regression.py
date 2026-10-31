"""Controlled latency investigation using an independent contact fixture."""

from evaluation import score_case
from faults import FaultConfig, inject_faults
from motion import Scenario, sample_truth
from replay import replay


REFERENCE_CONTACT_TIME_S = 6.0


def run_latency_case(latency_s):
    """Run one latency arm without writing files or changing the trajectory."""

    scenario = Scenario(
        scenario_id="latency_regression",
        initial_gap_m=30.0,
        ego_speed_mps=10.0,
        lead_speed_mps=5.0,
        timestep_s=1.0,
        sample_count=7,
    )

    config = FaultConfig(
        mode="clean" if latency_s == 0 else "latency",
        latency_s=latency_s,
    )

    policy = {
        "warning_threshold_s": 2.0,
        "max_age_s": 3.0,
        "pre_event_window_s": 3.0,
        "minimum_useful_lead_s": 1.0,
        "decision_clock": "fixed 0.5 s",
    }

    truth = sample_truth(scenario)
    observations, audit = inject_faults(truth, config)

    # Fixed across all arms; do not derive this clock from the contact event.
    decision_times_s = [index * 0.5 for index in range(13)]

    replay_result = replay(
        observations,
        decision_times_s,
        warning_threshold_s=policy["warning_threshold_s"],
        max_age_s=policy["max_age_s"],
        scenario_id=scenario.scenario_id,
        horizon_s=scenario.horizon_s,
    )

    score = score_case(
        replay_result.decisions,
        reference_contact_time_s=REFERENCE_CONTACT_TIME_S,
        horizon_s=scenario.horizon_s,
        pre_event_window_s=policy["pre_event_window_s"],
        minimum_useful_lead_s=policy["minimum_useful_lead_s"],
    )

    return {
        "scenario": scenario,
        "truth": truth,
        "fault_config": config,
        "observations": observations,
        "audit": audit,
        "decision_times_s": decision_times_s,
        "replay": replay_result,
        "score": score,
        "policy": policy,
        "reference_contact_time_s": REFERENCE_CONTACT_TIME_S,
    }
