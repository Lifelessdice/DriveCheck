"""Run a configured M2 experiment or the M4 offline release workflow."""

import argparse
import json
from pathlib import Path
import sys

from experiments import DEFAULT_CONFIG, run
from m1 import ROOT
from release_config import (
    _reject_constant,
    _unique_keys,
)
from release_report import generate
from release_runner import run as run_release


def schema_at(path):
    path = Path(path)
    path = (path if path.is_absolute() else ROOT / path).resolve()

    if not path.is_relative_to(ROOT):
        raise ValueError("configuration must remain inside the project")

    value = json.loads(
        path.read_text("utf-8"),
        object_pairs_hook=_unique_keys,
        parse_constant=_reject_constant,
    )

    if not isinstance(value, dict):
        raise ValueError("configuration must be a JSON object")

    return value.get("schema_version")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
    )
    parser.add_argument(
        "--all-plots",
        action="store_true",
    )

    args = parser.parse_args(argv)

    try:
        schema = schema_at(args.config)

        if schema == "drivecheck.m2.v1":
            if args.all_plots:
                raise ValueError("--all-plots applies to M4 only")

            output = args.output_dir or ROOT / "outputs" / "m2-first"

            manifest = run(args.config, output)

            completed = sum(row["status"] == "complete" for row in manifest["cases"])

            print(
                f"{manifest['status']}: "
                f"{completed}/"
                f"{manifest['expected_case_count']} "
                "cases complete"
            )
            print(f"Outputs: {(ROOT / output).resolve()}")

            if manifest["error"]:
                print(
                    manifest["error"],
                    file=sys.stderr,
                )

            return 0 if manifest["status"] == "complete" else 1

        if schema != "drivecheck.m4.v1":
            raise ValueError("unsupported experiment schema")

        if args.output_dir is None:
            raise ValueError("M4 requires an explicit fresh --output-dir")

        machine = run_release(
            args.config,
            args.output_dir,
        )

    except (ValueError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    try:
        package = generate(
            args.output_dir,
            all_plots=args.all_plots,
        )
    except Exception as error:
        print(
            "Report validation/packaging failed: " f"{error}",
            file=sys.stderr,
        )
        return 1

    print(
        f"machine-results {machine['status']}; " f"offline-report {package['status']}"
    )

    print("Report: " f"{(ROOT / args.output_dir / 'report' / 'report.html').resolve()}")

    if package["error"]:
        print(
            package["error"],
            file=sys.stderr,
        )

    return 0 if machine["status"] == package["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
