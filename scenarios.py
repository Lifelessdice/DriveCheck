from dataclasses import dataclass

from motion import Scenario


@dataclass(frozen=True)
class Fixture:
    """A scenario paired with independently calculated reference values."""

    scenario: Scenario
    reference_contact_time_s: float | None
    reference_final_gap_m: float
    reference_basis: str


def m1_fixtures():
    """Return the three independently specified M1 study cases."""
    return [
        Fixture(
            scenario=Scenario(
                scenario_id="constant_speed_original",
                initial_gap_m=30,
                ego_speed_mps=20,
                lead_speed_mps=15,
                timestep_s=1,
                sample_count=5,
            ),
            reference_contact_time_s=None,
            reference_final_gap_m=10.0,
            reference_basis=(
                "gap=30-5t; final gap at 4 s is 10 m. "
                "Contact at 6 s lies outside the 4 s horizon."
            ),
        ),
        Fixture(
            scenario=Scenario(
                scenario_id="lead_braking_contact",
                initial_gap_m=30,
                ego_speed_mps=20,
                lead_speed_mps=15,
                timestep_s=1,
                sample_count=6,
                brake_start_s=1,
                lead_deceleration_mps2=5,
            ),
            reference_contact_time_s=3.3166247903554,
            reference_final_gap_m=-32.5,
            reference_basis=(
                "During braking, gap=27.5-2.5t^2, giving contact "
                "at sqrt(11) s. Lead stops at 4 s with rear x=67.5 m; "
                "ego front at 5 s is 100 m, giving gap=-32.5 m."
            ),
        ),
        Fixture(
            scenario=Scenario(
                scenario_id="lead_braking_noncontact",
                initial_gap_m=40,
                ego_speed_mps=10,
                lead_speed_mps=20,
                timestep_s=1,
                sample_count=9,
                brake_start_s=1,
                lead_deceleration_mps2=5,
            ),
            reference_contact_time_s=None,
            reference_final_gap_m=20.0,
            reference_basis=(
                "Lead travels 20 m before braking and 40 m while "
                "braking, then stops at 5 s with rear x=100 m. "
                "Ego front at 8 s is 80 m. Contact would occur "
                "at 10 s, outside the 8 s horizon."
            ),
        ),
    ]
