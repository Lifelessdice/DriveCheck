import argparse
import csv
import hashlib
import json
import math
import platform
from dataclasses import asdict, fields
from importlib import metadata
from pathlib import Path

from motion import TruthSample, first_contact_time, sample_truth, truth_at
from scenarios import m1_fixtures

ROOT = Path(__file__).resolve().parent
SCHEMA_VERSION = "drivecheck.truth.v1"

SOURCE_FILES = (
    "motion.py",
    "test_motion.py",
    "scenarios.py",
    "m1.py",
    "test_m1.py",
    "requirements.txt",
)

UNITS = {
    "time": "s",
    "position_and_gap": "m",
    "speed": "m/s",
    "deceleration": "m/s^2",
}


def sha256(path):
    """Identify the exact bytes stored in a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    """Write readable JSON while rejecting NaN and infinity."""
    path.write_text(
        json.dumps(value, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def provenance():
    """Record source bytes and the installed runtime versions."""
    missing = [name for name in SOURCE_FILES if not (ROOT / name).is_file()]

    if missing:
        raise ValueError(
            f"Missing provenance files: {', '.join(missing)}. "
            "Create all block files and requirements.txt before running."
        )

    packages = {
        distribution.metadata.get("Name", "unknown"): distribution.version
        for distribution in metadata.distributions()
    }

    return {
        "generator": "DriveCheck M1",
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "packages": dict(sorted(packages.items())),
        "source_sha256": {name: sha256(ROOT / name) for name in SOURCE_FILES},
        "seed": None,
        "randomness": "none",
    }


def preflight(output_dir, fixtures):
    """Validate every destination before creating or writing files."""
    if not fixtures:
        raise ValueError("At least one fixture is required")

    identifiers = [fixture.scenario.scenario_id for fixture in fixtures]

    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Scenario IDs must be unique")

    allowed = (ROOT / "outputs").resolve()

    if allowed != ROOT / "outputs":
        raise ValueError("The outputs directory must stay inside the project")

    output = (
        ROOT / "outputs" / "m1-study" if output_dir is None else Path(output_dir)
    ).resolve()

    if output == allowed or not output.is_relative_to(allowed):
        raise ValueError("Use a subfolder inside the project's outputs directory")

    if output.exists() and not output.is_dir():
        raise ValueError("The output destination must be a directory")

    destinations = [output / "manifest.json"]

    for identifier in identifiers:
        destinations.extend(
            output / f"{identifier}.{suffix}" for suffix in ("csv", "json", "png")
        )

    original_csv = (ROOT / "outputs" / "constant_speed.csv").resolve()
    resolved_destinations = []

    for destination in destinations:
        resolved = destination.resolve()

        # Existing symlinks must not redirect an artifact elsewhere.
        if resolved.parent != output or not resolved.is_relative_to(allowed):
            raise ValueError(f"Unsafe output destination: {destination.name}")

        if resolved == original_csv:
            raise ValueError("The original CSV snapshot is protected")

        if destination.exists() and not destination.is_file():
            raise ValueError(f"Expected a file destination: {destination.name}")

        resolved_destinations.append(resolved)

    if len(resolved_destinations) != len(set(resolved_destinations)):
        raise ValueError("Output destinations must not alias each other")

    return output


def matches(actual, expected):
    """Compare absent events explicitly and finite numbers within tolerance."""
    if actual is None or expected is None:
        return actual is expected

    return (
        math.isfinite(actual)
        and math.isfinite(expected)
        and math.isclose(actual, expected, rel_tol=0, abs_tol=1e-9)
    )


def save_plot(path, scenario, samples, event):
    """Plot the analytic trajectory alongside the saved sample grid."""
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    horizon = scenario.horizon_s
    times = {horizon * index / 400 for index in range(401)}
    times.update(row.time_s for row in samples)

    markers = [(horizon, f"Horizon {horizon:g} s", "gray", ":")]

    stop_time = scenario.stop_time_s

    if stop_time is not None:
        for time_s, label in (
            (scenario.brake_start_s, "Braking starts"),
            (stop_time, "Lead stops"),
        ):
            if 0 <= time_s <= horizon:
                times.add(time_s)
                markers.append((time_s, f"{label}: {time_s:g} s", "darkorange", "--"))

    if event is not None:
        times.add(event)
        markers.append((event, f"Contact {event:.6f} s", "red", "-."))

    states = [truth_at(scenario, time_s) for time_s in sorted(times)]

    fig, (gap_ax, speed_ax) = plt.subplots(
        2,
        1,
        sharex=True,
        figsize=(10, 7.5),
        layout="constrained",
    )

    fig.suptitle(f"{scenario.scenario_id}: clean kinematic truth")

    gap_ax.plot(
        [row.time_s for row in states],
        [row.gap_m for row in states],
        label="Analytic gap",
    )
    gap_ax.scatter(
        [row.time_s for row in samples],
        [row.gap_m for row in samples],
        label="Saved samples",
        s=24,
        zorder=3,
    )
    gap_ax.axhline(
        0,
        color="black",
        linewidth=1,
        label="Touching: gap = 0 m",
    )
    gap_ax.set_ylabel("Bumper gap (m)")

    if event is None:
        gap_ax.set_title(f"No contact within the {horizon:g} s horizon")
    else:
        gap_ax.set_title("Signed paths continue after contact; no impact response")

    speed_ax.plot(
        [row.time_s for row in states],
        [row.ego_speed_mps for row in states],
        label="Ego",
    )
    speed_ax.plot(
        [row.time_s for row in states],
        [row.lead_speed_mps for row in states],
        label="Lead",
    )
    speed_ax.set_ylabel("Forward speed (m/s)")
    speed_ax.set_xlabel("Elapsed simulation time (s)")
    speed_ax.set_ylim(bottom=0)

    for axis in (gap_ax, speed_ax):
        for time_s, label, color, style in markers:
            axis.axvline(
                time_s,
                color=color,
                linestyle=style,
                linewidth=1,
                label=label,
            )

        axis.set_xlim(0, max(horizon, 0.1))
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8, ncol=2)

    try:
        fig.savefig(
            path,
            dpi=140,
            format="png",
            metadata={
                "Software": f"DriveCheck M1 / Matplotlib {matplotlib.__version__}"
            },
        )
    finally:
        plt.close(fig)


def run(output_dir=None, fixtures=None):
    """Check and export all requested cases, recording success or failure."""
    fixtures = list(m1_fixtures() if fixtures is None else fixtures)

    output = preflight(output_dir, fixtures)
    context = provenance()

    # Preflight and source reads finish before any output is written.
    output.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "status": "running",
        "provenance": context,
        "cases": [],
    }
    write_json(output / "manifest.json", manifest)

    current_case = None

    try:
        for fixture in fixtures:
            scenario = fixture.scenario
            current_case = scenario.scenario_id

            samples = sample_truth(scenario)
            event = first_contact_time(scenario)
            final_gap = samples[-1].gap_m

            if not (
                matches(event, fixture.reference_contact_time_s)
                and matches(final_gap, fixture.reference_final_gap_m)
            ):
                raise ValueError(
                    f"{current_case}: independent reference mismatch; "
                    f"computed contact={event}, final gap={final_gap}"
                )

            csv_path = output / f"{current_case}.csv"
            json_path = output / f"{current_case}.json"
            png_path = output / f"{current_case}.png"

            with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
                writer = csv.DictWriter(
                    csv_file,
                    fieldnames=[field.name for field in fields(TruthSample)],
                )
                writer.writeheader()
                writer.writerows(asdict(row) for row in samples)

            computed = {
                "first_contact_time_s": event,
                "final_gap_m": final_gap,
            }

            sidecar = {
                "schema_version": SCHEMA_VERSION,
                "configuration": asdict(scenario),
                "family": (
                    "lead_braking"
                    if scenario.lead_deceleration_mps2 > 0
                    else "constant_speed"
                ),
                "horizon_s": scenario.horizon_s,
                "units": UNITS,
                "axis": (
                    "+x forward; ego front initially 0; "
                    "lead rear initially initial_gap_m"
                ),
                "sampling": (
                    "sample IDs start at 0; time=ID*timestep; "
                    "horizon=(sample_count-1)*timestep"
                ),
                "contact_policy": (
                    "First contact on the inclusive horizon; initial "
                    "gap<=0 gives event 0. Endpoint allowance is 32 ULPs "
                    "of the actual phase endpoint time scale."
                ),
                "model_limit": (
                    "Negative gap is virtual overlap of prescribed paths; "
                    "impact dynamics are not simulated."
                ),
                "truth_only": True,
                "reference": {
                    "first_contact_time_s": fixture.reference_contact_time_s,
                    "final_gap_m": fixture.reference_final_gap_m,
                    "basis": fixture.reference_basis,
                },
                "computed": computed,
                "reference_check": "passed",
                "provenance": context,
            }

            write_json(json_path, sidecar)
            save_plot(png_path, scenario, samples, event)

            manifest["cases"].append(
                {
                    "scenario_id": current_case,
                    "rows": len(samples),
                    "horizon_s": scenario.horizon_s,
                    "computed": computed,
                    "reference_check": "passed",
                    "artifacts": {
                        path.name: sha256(path)
                        for path in (csv_path, json_path, png_path)
                    },
                }
            )

        manifest["status"] = "complete"

    except Exception as error:
        manifest["status"] = "failed"
        manifest["error"] = f"{current_case}: {type(error).__name__}: {error}"
        raise

    finally:
        write_json(output / "manifest.json", manifest)

    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export DriveCheck M1 clean truth")
    parser.add_argument("--output-dir", type=Path, default=None)
    arguments = parser.parse_args()

    result = run(output_dir=arguments.output_dir)

    for case in result["cases"]:
        computed = case["computed"]
        print(
            f"{case['scenario_id']}: "
            f"rows={case['rows']}, "
            f"horizon={case['horizon_s']:g} s, "
            f"contact={computed['first_contact_time_s']}, "
            f"final gap={computed['final_gap_m']:g} m"
        )

    print(f"Run status: {result['status']}")
