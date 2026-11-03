"""Run and package the frozen C1 paired comparison without changing the M4 CLI."""

import argparse
from pathlib import Path
import sys

from c1_comparison import run
from c1_report import render


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest = run(args.config, args.output_dir)
    except (ValueError, FileNotFoundError) as error:
        parser.error(str(error))
    except Exception as error:
        if args.debug:
            raise
        print(f"Comparison execution failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    try:
        package = render(args.output_dir)
    except Exception as error:
        if args.debug:
            raise
        print(f"Comparison report failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print(f"C1 machine {manifest['status']}; report {package['status']}")
    print(f"Report: {(args.output_dir / 'report' / 'report.html').resolve()}")
    return 0 if manifest["status"] == package["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
