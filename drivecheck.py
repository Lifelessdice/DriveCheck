"""Run the configured offline DriveCheck experiment."""

import argparse
import sys
from pathlib import Path

from experiments import DEFAULT_CONFIG, run
from m1 import ROOT


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "outputs" / "m2-first",
    )
    args = parser.parse_args(argv)

    try:
        manifest = run(args.config, args.output_dir)
    except (ValueError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    completed = sum(case["status"] == "complete" for case in manifest["cases"])

    print(
        f"{manifest['status']}: "
        f"{completed}/{manifest['expected_case_count']} cases complete"
    )
    print(f"Outputs: {(ROOT / args.output_dir).resolve()}")

    if manifest["error"]:
        print(manifest["error"], file=sys.stderr)

    return 0 if manifest["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
