"""Reproduce the frozen M4 release in a new environment and source snapshot."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
INPUT_FILES = (
    "motion.py", "scenarios.py", "m1.py", "observations.py", "warning_policy.py",
    "replay.py", "evaluation.py", "experiments.py", "reporting.py", "drivecheck.py",
    "faults.py", "stop_and_go.py", "m3_regression.py", "m3_study.py",
    "release_config.py", "release_runner.py", "release_report.py",
    "test_motion.py", "test_m1.py", "test_m2.py", "test_replay.py",
    "test_evaluation.py", "test_report.py", "test_m3_faults.py",
    "test_m3_injection.py", "test_m3_scenarios.py", "test_m3_boundaries.py",
    "test_m3_regression.py", "test_m3_study.py", "test_m4_config.py",
    "test_m4_runner.py", "test_m4_report.py", "test_environment_lock.py",
    "tools/lock_requirements.py", "tools/reproduce.py", "ruff.toml",
    "requirements.txt", "requirements-lock.txt", "configs/m2-experiment.json",
    "configs/m2-age-075.json", "configs/m4-release.json", ".github/workflows/ci.yml",
)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(directory):
    return {
        path.relative_to(directory).as_posix(): file_hash(path)
        for path in sorted(directory.rglob("*")) if path.is_file()
    }


def write_record(path, value):
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8", newline="\n",
    )


def verify_run(path):
    """Check the full default release and its current-checkout provenance."""
    from release_report import (
        check_links, contained, digest, load_machine, package_hashes, read_json,
        selected,
    )

    directory, machine = load_machine(path)
    package = read_json(directory / "release-manifest.json")
    if (
        machine["status"] != "complete" or machine["error"] is not None
        or package.get("schema") != "drivecheck.m4.report.v1"
        or package.get("stage") != "offline-report"
        or package.get("status") != "complete"
        or package.get("machine_status") != "complete"
        or package.get("error") is not None
    ):
        raise ValueError("release is not completely packaged")
    rows = machine["cases"] + machine["regression_cases"]
    if len(machine["cases"]) != 76 or len(machine["regression_cases"]) != 5:
        raise ValueError("expected 76 main cases and five separate diagnostics")
    if any(row["status"] != "complete" for row in rows):
        raise ValueError("release contains an incomplete case")
    actual = package_hashes(directory)
    if package.get("artifact_sha256") != actual:
        raise ValueError("package hashes do not cover the exact file inventory")
    machine_files = {
        name: value for name, value in actual.items()
        if name != "manifest.json" and not name.startswith("report/")
    }
    if machine["artifact_sha256"] != machine_files:
        raise ValueError("machine hashes do not cover the exact file inventory")
    if package.get("machine_manifest_sha256") != digest(directory / "manifest.json"):
        raise ValueError("package refers to a different machine manifest")
    expected_plots = [row["case_id"] for row in rows if selected(row, False)]
    actual_plots = {
        path.stem for path in (directory / "report").glob("*.png")
    }
    if (
        package.get("plot_case_ids") != expected_plots
        or len(expected_plots) != 11 or actual_plots != set(expected_plots)
    ):
        raise ValueError("default plot selection disagrees with saved artifacts")
    links = check_links(directory)
    if links != package.get("local_link_count") or links != 421:
        raise ValueError("default report link inventory disagrees")
    for sources in (
        machine["provenance"]["source_sha256"],
        package["renderer"]["source_sha256"],
    ):
        for name, expected in sources.items():
            if digest(contained(ROOT, name)) != expected:
                raise ValueError(f"checkout provenance mismatch: {name}")
    provenance = machine["provenance"]
    config = contained(ROOT, provenance["input_configuration_path"])
    if digest(config) != provenance["input_configuration_sha256"]:
        raise ValueError("input configuration provenance mismatch")
    return {
        "status": "complete", "main_cases": 76, "diagnostic_cases": 5,
        "machine_hashes": len(machine_files), "package_hashes": len(actual),
        "files": len(actual) + 1, "plots": len(expected_plots), "local_links": links,
    }


def run_python(python, arguments, cwd, log):
    """Capture each command and stop before subsequent stages on failure."""
    environment = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE"):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    print(f"Running {log.name}", flush=True)
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run(
            [str(python), "-E", "-s", *map(str, arguments)],
            cwd=cwd, env=environment, stdout=stream, stderr=subprocess.STDOUT,
            check=False,
        )
    if result.returncode:
        print(log.read_text("utf-8", errors="replace")[-6000:], file=sys.stderr)
        raise RuntimeError(f"command exited {result.returncode}; see {log}")


def reproduce(wheel_source=None):
    output_root = ROOT / "outputs"
    if output_root.resolve() != output_root:
        raise ValueError("outputs must not redirect outside the checkout")
    parent = output_root / "m4-environment"
    if parent.resolve() != parent:
        raise ValueError("reproduction directory must not be redirected")
    parent.mkdir(parents=True, exist_ok=True)
    work = parent / ("reproduction-" + uuid.uuid4().hex)
    work.mkdir()
    print(f"Reproduction evidence: {work}", flush=True)
    record = {"schema": "drivecheck.m4.reproduction.v1", "status": "running"}
    write_record(work / "reproduction.json", record)
    try:
        wheels = work / "wheelhouse"
        wheels.mkdir()
        if wheel_source is None:
            run_python(
                sys.executable,
                ["-m", "pip", "--isolated", "download", "--index-url",
                 "https://pypi.org/simple", "--only-binary=:all:", "--dest",
                 wheels, "-r", "requirements.txt", "pip==26.2.1", "ruff==0.14.0"],
                ROOT, work / "download.log",
            )
        else:
            source = Path(wheel_source).resolve()
            for wheel in source.iterdir():
                if not wheel.is_file() or wheel.suffix != ".whl":
                    raise ValueError(f"unexpected cached wheel entry: {wheel.name}")
                shutil.copyfile(wheel, wheels / wheel.name)
        run_python(
            sys.executable, ["tools/lock_requirements.py", "--wheelhouse", wheels],
            ROOT, work / "lock.log",
        )
        environment = work / "venv"
        run_python(
            sys.executable, ["-m", "venv", environment], ROOT, work / "venv.log",
        )
        python = environment / "Scripts" / "python.exe"
        run_python(
            python,
            ["-m", "pip", "--isolated", "install", "--no-index", "--find-links",
             wheels, "--require-hashes", "--only-binary=:all:", "--force-reinstall",
             "-r", "requirements-lock.txt"],
            ROOT, work / "install.log",
        )
        run_python(python, ["-m", "pip", "--isolated", "check"], ROOT, work / "pip-check.log")
        run_python(
            python, ["-m", "pip", "list", "--format=json"], ROOT,
            work / "installed-packages.json",
        )
        run_python(
            python, ["-m", "ruff", "check", "--config", "ruff.toml", "."],
            ROOT, work / "lint-original.log",
        )
        snapshot = work / "source"
        snapshot.mkdir()
        input_hashes = {}
        for name in INPUT_FILES:
            source = ROOT / name
            destination = snapshot / name
            if not source.is_file() or not source.resolve().is_relative_to(ROOT):
                raise ValueError(f"missing or redirected input: {name}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            expected = file_hash(source)
            shutil.copyfile(source, destination)
            if file_hash(destination) != expected:
                raise ValueError(f"copy mismatch: {name}")
            input_hashes[name] = expected
        write_record(work / "input-sha256.json", input_hashes)
        (snapshot / "outputs").mkdir()
        run_python(
            sys.executable, ["-m", "unittest", "-v"], ROOT, work / "tests-original.log",
        )
        baseline = work / "baseline"
        run_python(
            sys.executable,
            ["drivecheck.py", "--config", "configs/m4-release.json", "--output-dir", baseline],
            ROOT, work / "report-original.log",
        )
        record["baseline"] = verify_run(baseline)
        run_python(
            python,
            ["-m", "ruff", "check", "--no-respect-gitignore", "--config", "ruff.toml", "."],
            snapshot, work / "lint-copied.log",
        )
        run_python(
            python, ["-m", "unittest", "-v"], snapshot, work / "tests-copied.log",
        )
        run_python(
            python,
            ["drivecheck.py", "--config", "configs/m4-release.json",
             "--output-dir", "outputs/reproduced"],
            snapshot, work / "report-copied.log",
        )
        reproduced = snapshot / "outputs" / "reproduced"
        audit_log = work / "audit-copied.json"
        run_python(
            python, ["-m", "tools.reproduce", "--verify-run", reproduced],
            snapshot, audit_log,
        )
        record["reproduced"] = json.loads(audit_log.read_text("utf-8"))
        a, b = inventory(baseline), inventory(reproduced)
        differences = sorted(
            name for name in a.keys() | b.keys() if a.get(name) != b.get(name)
        )
        record["different_files"] = differences
        record["input_sha256"] = input_hashes
        record["wheel_sha256"] = inventory(wheels)
        if differences:
            raise ValueError(f"reproduction differs in {len(differences)} files")
        if any(file_hash(ROOT / name) != expected for name, expected in input_hashes.items()):
            raise ValueError("source changed during reproduction")
        record["status"] = "complete"
        write_record(work / "reproduction.json", record)
        print(json.dumps(record, indent=2), flush=True)
        return work
    except Exception as exc:
        record["status"] = "failed"
        record["error"] = f"{type(exc).__name__}: {exc}"
        write_record(work / "reproduction.json", record)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheelhouse", type=Path, help="reuse already downloaded wheels")
    parser.add_argument("--verify-run", type=Path, help="audit a default release against this checkout")
    args = parser.parse_args(argv)
    try:
        if args.verify_run is not None:
            if args.wheelhouse is not None:
                raise ValueError("--verify-run cannot be combined with --wheelhouse")
            print(json.dumps(verify_run(args.verify_run), indent=2))
        else:
            reproduce(args.wheelhouse)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Reproduction failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
