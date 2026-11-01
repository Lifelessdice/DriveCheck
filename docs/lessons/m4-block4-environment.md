# M4 Block 4 — Lock dependencies and reproduce from clean inputs

Prepared 1 November 2026. This is complete learner-run teaching material, also supplied directly in chat. No helper, lock, lint configuration, dependency installation or reproduction below has been implemented/run by the assistant. Blocks 1–3 are accepted locally; clean-environment reproduction and CI remain pending.

The fixed source filenames in this block are `tools/lock_requirements.py`, `test_environment_lock.py` and `ruff.toml`. The helper generates one fixed `requirements-lock.txt`. Generated experiment folders receive a timestamp and random suffix automatically so previous evidence is preserved. Continue on `feature/m4-reproducible-release`.

## Why this matters

`requirements.txt` pins package versions. A wheel is an installable package archive; SHA-256 identifies its exact bytes. The new lock binds each selected package version to the actual downloaded wheel. We preserve all 12 current runtime pins and add fixed tooling pins: pip 26.2.1 and Ruff 0.14.0. These are chosen reproducible versions, not claims about latest releases. The target is the observed CPython 3.14.7 on Windows x64. This wheel lock does not promise installation on other platforms.

The existing interpreter downloads compatible wheels without installing them. A new environment installs only those local, hashed wheels. An explicit source copy then runs the whole suite and full report without the old environment, private context, editor files or old generated reports as inputs. This is new-source/new-package-environment reproduction on this machine, not a fresh operating system or remote CI result.

The helper rejects missing, duplicate, unexpected and wrong-version wheels. It reads metadata without extracting/importing archives. Matching existing lock content is allowed; different existing content is preserved and rejected. pip's dependency resolver and `pip check` provide the subsequent dependency-consistency check.

Primary references checked 1 November 2026: [pip download](https://pip.pypa.io/en/stable/cli/pip_download/), [hash-checked installs](https://pip.pypa.io/en/stable/topics/secure-installs/), [Ruff configuration](https://docs.astral.sh/ruff/configuration/), [pinned Ruff metadata](https://pypi.org/pypi/ruff/0.14.0/json) and [pinned pip metadata](https://pypi.org/pypi/pip/26.2.1/json). Both tooling packages list MIT licensing; their actual downloaded wheels still have to pass local installation/checks.

## 1. Save `tools/lock_requirements.py`

Create the `tools` directory if needed. It is a source directory, separate from generated output.

```python
"""Create a platform-specific hash lock from downloaded wheel bytes."""

import argparse
from email.parser import Parser
import hashlib
from pathlib import Path
import platform
import re
import struct
import sys
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
TOOL_PINS = {"pip": "26.2.1", "ruff": "0.14.0"}


def canonical_name(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def read_pins(path):
    """Accept explicit version pins, blank lines and full-line comments."""
    pins = {}
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(
            r"([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9.!+_-]*)",
            line,
        )
        if match is None:
            raise ValueError(f"expected a name==version pin: {line}")
        name, version = match.groups()
        name = canonical_name(name)
        if name in pins:
            raise ValueError(f"duplicate requirement: {name}")
        pins[name] = version
    if not pins:
        raise ValueError("runtime requirements are empty")
    return pins


def build_lock(requirements, wheelhouse):
    expected = read_pins(requirements)
    if expected.keys() & TOOL_PINS.keys():
        raise ValueError("runtime requirements must exclude the tooling pins")
    expected.update(TOOL_PINS)
    found = {}
    for wheel in sorted(Path(wheelhouse).iterdir()):
        if not wheel.is_file() or wheel.suffix != ".whl":
            raise ValueError(f"unexpected wheelhouse entry: {wheel.name}")
        with ZipFile(wheel) as archive:
            metadata_names = [
                name for name in archive.namelist()
                if name.endswith(".dist-info/METADATA")
                and len(name.split("/")) == 2
            ]
            if len(metadata_names) != 1:
                raise ValueError(f"expected one METADATA file: {wheel.name}")
            metadata = Parser().parsestr(
                archive.read(metadata_names[0]).decode("utf-8"),
                headersonly=True,
            )
        if len(metadata.get_all("Name", [])) != 1 or len(
            metadata.get_all("Version", [])
        ) != 1:
            raise ValueError(f"invalid package identity: {wheel.name}")
        name = canonical_name(metadata["Name"].strip())
        version = metadata["Version"].strip()
        if name not in expected:
            raise ValueError(f"unexpected package: {name}")
        if version != expected[name]:
            raise ValueError(f"wrong version for {name}: {version}")
        if name in found:
            raise ValueError(f"duplicate wheel for {name}")
        found[name] = hashlib.sha256(wheel.read_bytes()).hexdigest()
    missing = sorted(expected.keys() - found.keys())
    if missing:
        raise ValueError(f"missing wheels: {missing}")
    lines = [
        "# CPython 3.14.7 / Windows x64; selected wheel bytes.",
        "# Runtime pins from requirements.txt; tooling pins from lock_requirements.py.",
    ]
    lines.extend(
        f"{name}=={expected[name]} --hash=sha256:{found[name]}"
        for name in sorted(expected)
    )
    return "\n".join(lines) + "\n"


def save_lock(path, content):
    """Allow an identical lock; preserve any different existing lock."""
    path = Path(path)
    payload = content.encode("utf-8")
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"different lock already exists: {path}")
        return
    with path.open("xb") as stream:
        stream.write(payload)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheelhouse", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if (
            platform.python_implementation() != "CPython"
            or platform.python_version() != "3.14.7"
            or platform.system() != "Windows"
            or struct.calcsize("P") != 8
            or platform.machine().lower() not in {"amd64", "x86_64"}
        ):
            raise ValueError("this lock targets CPython 3.14.7 / Windows x64")
        content = build_lock(ROOT / "requirements.txt", args.wheelhouse)
        output = ROOT / "requirements-lock.txt"
        save_lock(output, content)
        print(f"Verified hash lock: {output}")
    except (OSError, ValueError, BadZipFile) as exc:
        print(f"Lock failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 2. Save `test_environment_lock.py`

These tests use synthetic ZIP archives, not downloaded software. They independently check the expected hash and refusal cases; actual package compatibility is checked by installation and the full project run.

```python
"""Check lock identity, exact-byte hashes and preservation guards."""

import hashlib
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from tools.lock_requirements import ROOT, TOOL_PINS, build_lock, save_lock


class EnvironmentLockTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "outputs").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.requirements = self.root / "requirements.txt"
        self.requirements.write_text("Example_pkg==1.2\n", encoding="utf-8")
        self.wheels = self.root / "wheels"
        self.wheels.mkdir()
        self.example = self.wheel("Example.pkg", "1.2", "example.whl")
        for name, version in TOOL_PINS.items():
            self.wheel(name, version, f"{name}.whl")

    def wheel(self, name, version, filename):
        path = self.wheels / filename
        with ZipFile(path, "w") as archive:
            archive.writestr(
                "package.dist-info/METADATA",
                f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n\n",
            )
        return path

    def test_metadata_identity_and_actual_byte_hash(self):
        result = build_lock(self.requirements, self.wheels)
        digest = hashlib.sha256(self.example.read_bytes()).hexdigest()
        self.assertIn(f"example-pkg==1.2 --hash=sha256:{digest}\n", result)
        pins = [line for line in result.splitlines() if not line.startswith("#")]
        self.assertEqual(len(pins), 3)
        self.assertEqual(pins, sorted(pins))
        self.assertEqual(result, build_lock(self.requirements, self.wheels))

    def test_missing_wheel(self):
        self.example.unlink()
        with self.assertRaisesRegex(ValueError, "missing wheels"):
            build_lock(self.requirements, self.wheels)

    def test_duplicate_normalized_identity(self):
        self.wheel("example-pkg", "1.2", "duplicate.whl")
        with self.assertRaisesRegex(ValueError, "duplicate wheel"):
            build_lock(self.requirements, self.wheels)

    def test_wrong_version(self):
        self.wheel("example-pkg", "9.9", "example.whl")
        with self.assertRaisesRegex(ValueError, "wrong version"):
            build_lock(self.requirements, self.wheels)

    def test_unexpected_package(self):
        self.wheel("unplanned", "1.0", "unplanned.whl")
        with self.assertRaisesRegex(ValueError, "unexpected package"):
            build_lock(self.requirements, self.wheels)

    def test_identical_lock_allowed_but_different_content_preserved(self):
        path = self.root / "requirements-lock.txt"
        save_lock(path, "first\n")
        save_lock(path, "first\n")
        with self.assertRaisesRegex(ValueError, "different lock"):
            save_lock(path, "second\n")
        self.assertEqual(path.read_bytes(), b"first\n")


if __name__ == "__main__":
    unittest.main()
```

## 3. Save `ruff.toml`; remove the known unused import

Lint checks source without running it. The selected rules check import/statement mistakes and undefined/unused names. They do not force a whole-project formatting rewrite. [Ruff's configuration](https://docs.astral.sh/ruff/configuration/) explains rule selection and exclusions.

```toml
required-version = "==0.14.0"
target-version = "py314"
extend-exclude = ["outputs", ".private", "practice_m1.py", "t_motion.py"]

[lint]
select = ["E4", "E7", "E9", "F"]
```

In `experiments.py`, replace the existing import containing unused `save_plot` with:

```python
from m1 import ROOT, matches, sha256, write_json
```

In `motion.py`, remove only these three unused import statements:

```python
import csv
import json
from pathlib import Path
```

Keep all other imports and executable logic. `reporting.py` imports and uses its own plot function; the unused import in `experiments.py` is not part of its API. Review any other lint diagnostics before changing code. Do not suppress a rule to get a green result or run bulk automatic fixes. Establish both comparison runs after all reviewed source fixes.

## 4. Download wheels, generate the lock and create a new environment

Run in one PowerShell session and keep that session open for the later blocks. This setup uses the network for downloads; installation then uses only the local wheelhouse. The function turns native-program failures into stopping errors. Its `-E -s` interpreter flags ignore Python environment overrides and user-site packages for each invocation while retaining the selected working directory for project imports. The old `.venv` is used for reading/downloading and creating the new environment; all package installation targets the new interpreter.

The dot-sourced `. { ... }` setup runs as one stopping block while retaining its function and variables in your current session. An `& { ... }` child scope here would hide variables needed by subsequent blocks. Continue only after setup finishes without an error. The single install uses `--force-reinstall` in the new environment so even a matching bootstrapped pip version is replaced by the selected hash-checked wheel; the original environment is unchanged.

```powershell
Set-Location 'E:\DriveCheck'
$ErrorActionPreference = 'Stop'

. {
function Invoke-DriveCheckPython {
    param([string]$Python, [string[]]$Argv)
    & $Python -E -s @Argv
    if ($LASTEXITCODE -ne 0) { throw "Python command failed with exit $LASTEXITCODE" }
}

$projectRoot = (Resolve-Path '.').Path
$originalPython = (Resolve-Path '.\.venv\Scripts\python.exe').Path
$runId = '{0}-{1}' -f (Get-Date -Format 'yyyyMMdd-HHmmss'), ([guid]::NewGuid().ToString('N').Substring(0, 8))
$workRoot = Join-Path $projectRoot "outputs\m4-environment\$runId"
if (Test-Path -LiteralPath $workRoot) { throw 'Generated work folder already exists' }
$wheelhouse = Join-Path $workRoot 'wheelhouse'
New-Item -ItemType Directory -Path $wheelhouse -Force | Out-Null
Write-Host "Reproduction evidence: $workRoot"

Invoke-DriveCheckPython $originalPython @('-m', 'unittest', '-v', 'test_environment_lock')
Invoke-DriveCheckPython $originalPython @('-m', 'pip', '--isolated', 'download', '--index-url', 'https://pypi.org/simple', '--only-binary=:all:', '--dest', $wheelhouse, '-r', 'requirements.txt', 'pip==26.2.1', 'ruff==0.14.0')
Invoke-DriveCheckPython $originalPython @('tools/lock_requirements.py', '--wheelhouse', $wheelhouse)

$freshEnv = Join-Path $workRoot 'venv'
Invoke-DriveCheckPython $originalPython @('-m', 'venv', $freshEnv)
$freshPython = Join-Path $freshEnv 'Scripts\python.exe'
Invoke-DriveCheckPython $freshPython @('-m', 'pip', '--isolated', 'install', '--no-index', '--find-links', $wheelhouse, '--require-hashes', '--only-binary=:all:', '--force-reinstall', '-r', 'requirements-lock.txt')
Invoke-DriveCheckPython $freshPython @('-m', 'pip', 'check')
Invoke-DriveCheckPython $freshPython @('-m', 'pip', 'list', '--format=json') | Tee-Object -FilePath (Join-Path $workRoot 'installed-packages.json')
Invoke-DriveCheckPython $freshPython @('-m', 'ruff', 'check', '.')
}
```

Expected, not yet observed: six helper tests pass; 14 selected package versions have hashes; installation and `pip check` succeed; lint says `All checks passed!`. A failed download does not justify unpinning versions or changing Python. Keep the error and investigate wheel availability. A differing pre-existing lock requires review rather than replacement. If lint fails, fix/review that finding, rerun lint, then continue. Preserve this PowerShell session's variables.

## 5. Copy only the required inputs and run both environments

The explicit allowlist includes all 17 existing production modules, all 15 existing test modules, the new helper/test, the three live configurations, both requirement files and lint configuration. Each copy's SHA-256 is checked. No Git checkout is required for this local check: new learner files may still be uncommitted. The generated input inventory ties this reproduction to their actual saved bytes.

The copied source sits beneath the original repository's ignored `outputs/` directory. Copied-source lint therefore uses `--no-respect-gitignore`, so the original repository's ignore rule cannot silently skip the snapshot. The copied `ruff.toml` still excludes its own generated output/practice paths. The discovery command should list the intended copied Python source/tests before the actual lint check.

```powershell
& {
    Invoke-DriveCheckPython $freshPython @('-m', 'ruff', 'check', '.')
    Invoke-DriveCheckPython $originalPython @('-m', 'unittest', '-v')
    $baseline = Join-Path $workRoot 'baseline'
    Invoke-DriveCheckPython $originalPython @('drivecheck.py', '--config', 'configs/m4-release.json', '--output-dir', $baseline)

    $sourceRoot = Join-Path $workRoot 'source'
    $files = @(
        'motion.py', 'scenarios.py', 'm1.py', 'observations.py', 'warning_policy.py',
        'replay.py', 'evaluation.py', 'experiments.py', 'reporting.py', 'drivecheck.py',
        'faults.py', 'stop_and_go.py', 'm3_regression.py', 'm3_study.py',
        'release_config.py', 'release_runner.py', 'release_report.py',
        'test_motion.py', 'test_m1.py', 'test_m2.py', 'test_replay.py',
        'test_evaluation.py', 'test_report.py', 'test_m3_faults.py',
        'test_m3_injection.py', 'test_m3_scenarios.py', 'test_m3_boundaries.py',
        'test_m3_regression.py', 'test_m3_study.py', 'test_m4_config.py',
        'test_m4_runner.py', 'test_m4_report.py', 'test_environment_lock.py',
        'tools/lock_requirements.py', 'ruff.toml', 'requirements.txt',
        'requirements-lock.txt', 'configs/m2-experiment.json',
        'configs/m2-age-075.json', 'configs/m4-release.json'
    )
    $inputHashes = [ordered]@{}
    foreach ($name in $files) {
        $source = Join-Path $projectRoot $name
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing input: $name" }
        $destination = Join-Path $sourceRoot $name
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination
        $before = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
        $after = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
        if ($before -ne $after) { throw "Copy mismatch: $name" }
        $inputHashes[$name] = $before.ToLowerInvariant()
    }
    $inputHashes | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $workRoot 'input-sha256.json') -Encoding UTF8
    New-Item -ItemType Directory -Path (Join-Path $sourceRoot 'outputs') -Force | Out-Null

    Push-Location $sourceRoot
    try {
        Invoke-DriveCheckPython $freshPython @('-m', 'ruff', 'check', '--no-respect-gitignore', '--show-files', '.')
        Invoke-DriveCheckPython $freshPython @('-m', 'ruff', 'check', '--no-respect-gitignore', '.')
        Invoke-DriveCheckPython $freshPython @('-m', 'unittest', '-v')
        Invoke-DriveCheckPython $freshPython @('drivecheck.py', '--config', 'configs/m4-release.json', '--output-dir', 'outputs/reproduced')
    }
    finally { Pop-Location }
}
```

Expected: the suite grows from 163 to 169 tests, with both full runs passing. Both full reports should complete 76 main cases plus five separate diagnostics. Identical relative config spelling is deliberate because configuration provenance records the supplied input path. Do not edit source between the two runs. The baseline is produced after lint fixes; earlier release snapshots remain preserved.

## 6. Verify completion, all hashes, links and repeatability

```powershell
$comparison = @'
import hashlib
import json
from pathlib import Path
import sys
from release_report import check_links

baseline, copied, evidence = map(Path, sys.argv[1:])

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

for directory in (baseline, copied):
    machine = json.loads((directory / 'manifest.json').read_text('utf-8'))
    package = json.loads((directory / 'release-manifest.json').read_text('utf-8'))
    if machine['status'] != 'complete' or package['status'] != 'complete':
        raise ValueError(f'incomplete run: {directory}')
    rows = machine['cases'] + machine['regression_cases']
    if len(machine['cases']) != 76 or len(machine['regression_cases']) != 5:
        raise ValueError('wrong case inventory')
    if any(row['status'] != 'complete' for row in rows):
        raise ValueError('a case is not complete')
    for manifest in (machine, package):
        if not manifest['artifact_sha256']:
            raise ValueError('empty hash inventory')
        for relative, expected in manifest['artifact_sha256'].items():
            target = (directory / relative).resolve()
            if not target.is_relative_to(directory.resolve()) or digest(target) != expected:
                raise ValueError(f'artifact mismatch: {relative}')
    if digest(directory / 'manifest.json') != package['machine_manifest_sha256']:
        raise ValueError('machine/package identity mismatch')
    if check_links(directory) != package['local_link_count'] or len(package['plot_case_ids']) != 11:
        raise ValueError('report links/plot inventory mismatch')

def inventory(directory):
    return {p.relative_to(directory).as_posix(): digest(p)
            for p in directory.rglob('*') if p.is_file()}

a, b = inventory(baseline), inventory(copied)
differences = sorted(name for name in a.keys() | b.keys() if a.get(name) != b.get(name))
record = {'status': 'complete' if not differences else 'failed',
          'baseline_file_count': len(a), 'reproduced_file_count': len(b),
          'different_files': differences}
(evidence / 'comparison.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
print(json.dumps(record, indent=2))
if differences:
    raise SystemExit(1)
'@

& {
    $baseline = Join-Path $workRoot 'baseline'
    $reproduced = Join-Path $workRoot 'source\outputs\reproduced'
    $comparisonSource = Join-Path $workRoot 'source'
    Push-Location $comparisonSource
    try {
        Invoke-DriveCheckPython $freshPython @('-c', $comparison, $baseline, $reproduced, $workRoot)
    }
    finally { Pop-Location }
    Start-Process -FilePath (Join-Path $reproduced 'report\report.html')
}
```

Expected: `comparison.json` says `complete`, both file counts are 357 and `different_files` is empty. Every listed machine/package artifact hash verifies, report links remain contained and existing, and the plot selection contains 11 cases. If scientific JSON/CSV differs, investigate source/config/seed/runtime evidence. If only images differ, investigate rendering dependencies/fonts rather than changing scientific tolerances. Do not claim reproduction until the actual comparison passes. Visually inspect the opened report, especially units, summary denominators and the saved pending-arrival failure.

Think through: why can a version pin accept different wheel bytes? Why would copying an old output folder fail to test whether the source can regenerate it? These are self-checks, not reply gates.

Checkpoint after this block: fixed hash lock, local lint, dependency consistency and same-machine clean-source/new-environment reproduction should be supported by actual learner output. Remote CI and final M4 integration remain next. Keep the new source/lock changes for the next reviewed selective Git checkpoint; do not stage generated `outputs/` or unrelated files.
