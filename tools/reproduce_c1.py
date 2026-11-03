"""Reproduce C1 from explicit copied sources in a new hash-locked environment."""

import argparse
from pathlib import Path
import platform
import shutil
import struct
import sys
import uuid

from tools.reproduce import INPUT_FILES, file_hash, inventory, run_python, write_record


ROOT = Path(__file__).resolve().parents[1]
C1_INPUT_FILES = (
    "c1_estimators.py", "c1_replay.py", "c1_comparison.py", "c1_report.py",
    "c1_compare.py", "configs/c1-comparison.json", "test_c1_estimators.py",
    "test_c1_replay.py", "test_c1_comparison.py", "test_c1_report.py",
    "test_c1_audit.py", "tools/verify_c1.py", "tools/reproduce_c1.py",
)


def reproduce(wheelhouse=None):
    """Keep original environments/runs; preserve failed evidence with its logs."""
    if (platform.python_implementation() != "CPython"
            or sys.version_info[:3] != (3, 14, 7) or sys.platform != "win32"
            or struct.calcsize("P") != 8):
        raise ValueError("the recorded lock target is CPython 3.14.7 / Windows x64")
    output_root = ROOT / "outputs"
    if output_root.resolve() != output_root:
        raise ValueError("outputs must not redirect outside the checkout")
    source_wheels = None if wheelhouse is None else Path(wheelhouse).resolve()
    if source_wheels is not None and (
            not source_wheels.is_relative_to(ROOT) or not source_wheels.is_dir()):
        raise ValueError("wheelhouse must be an existing project directory")
    work = output_root / ("c1-reproduction-" + uuid.uuid4().hex)
    work.mkdir(parents=True)
    print(f"C1 reproduction evidence: {work}", flush=True)
    record = {"schema": "drivecheck.c1.reproduction.v1", "status": "running",
              "python": platform.python_version(), "error": None}
    write_record(work / "reproduction.json", record)
    try:
        snapshot = work / "source"
        snapshot.mkdir()
        hashes = {}
        for name in dict.fromkeys((*INPUT_FILES, *C1_INPUT_FILES)):
            source = ROOT / name
            if not source.is_file() or not source.resolve().is_relative_to(ROOT):
                raise ValueError(f"missing or redirected source: {name}")
            destination = snapshot / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            hashes[name] = file_hash(source)
            shutil.copyfile(source, destination)
            if file_hash(destination) != hashes[name]:
                raise ValueError(f"copied input differs: {name}")
        write_record(work / "input-sha256.json", hashes)
        environment = work / "venv"
        run_python(sys.executable, ["-m", "venv", environment], ROOT, work / "venv.log")
        python = environment / "Scripts" / "python.exe"
        wheels = work / "wheelhouse"
        wheels.mkdir()
        if source_wheels is None:
            run_python(sys.executable, ["-m", "pip", "--isolated", "download",
                       "--index-url", "https://pypi.org/simple", "--require-hashes",
                       "--only-binary=:all:", "-r", snapshot / "requirements-lock.txt",
                       "--dest", wheels], ROOT, work / "download.log")
        else:
            for wheel in source_wheels.iterdir():
                if not wheel.is_file() or wheel.suffix != ".whl":
                    raise ValueError(f"unexpected wheelhouse entry: {wheel.name}")
                shutil.copyfile(wheel, wheels / wheel.name)
        run_python(python, ["-m", "pip", "--isolated", "install", "--no-index",
                   "--find-links", wheels, "--require-hashes", "--only-binary=:all:",
                   "--force-reinstall", "-r", snapshot / "requirements-lock.txt"],
                   snapshot, work / "install.log")
        run_python(python, ["-m", "pip", "check"], snapshot, work / "pip-check.log")
        run_python(python, ["-m", "pip", "list", "--format=json"], snapshot,
                   work / "installed-packages.json")
        run_python(python, ["-m", "ruff", "check", "--no-respect-gitignore",
                   "--config", "ruff.toml", "."], snapshot, work / "lint.log")
        run_python(python, ["-m", "unittest", "discover", "-v"], snapshot,
                   work / "tests-copied.log")
        baseline = work / "original-run"
        copied = snapshot / "outputs" / "comparison"
        run_python(sys.executable, ["c1_compare.py", "--config", "configs/c1-comparison.json",
                   "--output-dir", baseline], ROOT, work / "original-run.log")
        run_python(python, ["c1_compare.py", "--config", "configs/c1-comparison.json",
                   "--output-dir", copied], snapshot, work / "copied-run.log")
        run_python(sys.executable, ["-m", "tools.verify_c1", baseline], ROOT,
                   work / "audit-original.json")
        run_python(python, ["-m", "tools.verify_c1", copied], snapshot,
                   work / "audit-copied.json")
        a, b = inventory(baseline), inventory(copied)
        differences = sorted(name for name in a.keys() | b.keys() if a.get(name) != b.get(name))
        record.update(input_sha256=hashes, wheel_sha256=inventory(wheels),
                      original_run=str(baseline.relative_to(ROOT)),
                      copied_run=str(copied.relative_to(ROOT)),
                      original_file_count=len(a), copied_file_count=len(b),
                      different_files=differences)
        if differences:
            raise ValueError(f"reproduction differs in {len(differences)} files")
        if any(file_hash(ROOT / name) != expected for name, expected in hashes.items()):
            raise ValueError("source changed during reproduction")
        record["status"] = "complete"
    except Exception as error:
        record.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        write_record(work / "reproduction.json", record)
    print(f"C1 reproduction complete: {work / 'reproduction.json'}", flush=True)
    return work


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--wheelhouse", type=Path, help="reuse an existing project wheel cache")
    args = parser.parse_args(argv)
    try:
        reproduce(args.wheelhouse)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"C1 reproduction failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
