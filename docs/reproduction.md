# Reproduce DriveCheck

The checked target is **CPython 3.14.7 / Windows x64**. The source uses a project-local `.venv`; the hash lock records twelve runtime packages plus pip 26.2.1 and Ruff 0.14.0. No GPU, credentials, hosted service or simulator is required for experiments and reports.

## Prepare a new checkout

Run this only in a checkout without an existing `.venv`. It validates the exact interpreter before creating the environment and installs only the locked binary artifacts:

```powershell
Set-Location 'E:\DriveCheck'
& {
    if (Test-Path -LiteralPath '.venv') {
        throw 'An environment already exists; use the prepared-checkout commands below.'
    }
    py -3.14 -c "import platform, struct, sys; expected = platform.python_implementation() == 'CPython' and sys.version_info[:3] == (3, 14, 7) and sys.platform == 'win32' and struct.calcsize('P') == 8 and platform.machine().lower() in {'amd64', 'x86_64'}; sys.exit(0 if expected else 'Expected CPython 3.14.7 / Windows x64')"
    if ($LASTEXITCODE -ne 0) { throw 'Interpreter check failed' }
    py -3.14 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Environment creation failed' }
    .\.venv\Scripts\python.exe -E -s -m pip --isolated install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: --force-reinstall -r requirements-lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Hash-locked installation failed' }
}
```

Do not recreate a working environment to run the project. Other Python/platform combinations require separately checked wheel artifacts rather than removing hash checks.

## Generate the comparison and offline demo

From a prepared checkout, use **fresh** output directories:

```powershell
.\.venv\Scripts\python.exe c1_compare.py --config configs/c1-comparison.json --output-dir outputs/comparison-new
if ($LASTEXITCODE -ne 0) { throw 'Comparison failed; inspect the saved status/error.' }
.\.venv\Scripts\python.exe -m tools.verify_c1 outputs/comparison-new
if ($LASTEXITCODE -ne 0) { throw 'Comparison audit failed.' }
.\.venv\Scripts\python.exe -m tools.portfolio_demo --run outputs/comparison-new --output-dir outputs/portfolio-new
if ($LASTEXITCODE -ne 0) { throw 'Portfolio packaging failed.' }
Invoke-Item -LiteralPath .\outputs\portfolio-new\index.html
```

The comparison retains 76 development pairs, 76 evaluation pairs and five separate diagnostics. All 314 method records remain visible with explicit status. The output contains `manifest.json`, `configuration.json`, `frozen-selection.json`, `case-plan.json`, `summary.json`, `cases.csv`, per-case traces and `report/report.html`.

The short demo copies the complete audited evidence and adds an entry page. Keep its full folder together so relative links remain valid. The packager refuses an existing destination, redirected paths, a mismatched frozen narrative or different plot-to-case selection. It does not change source evidence.

Use [the demo script](demo.md) to walk through the mechanism, warning trade-off and unchanged case. [Architecture](architecture.md), [results](results.md) and [the investigation](c1-investigation.md) explain the contracts and findings.

## Check the full repository

```powershell
.\.venv\Scripts\python.exe -m unittest -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
.\.venv\Scripts\python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed.' }
.\.venv\Scripts\python.exe -m ruff check --config ruff.toml .
if ($LASTEXITCODE -ne 0) { throw 'Lint failed.' }
```

The published baseline passed 227 tests, dependency/lint checks, both complete experiment audits and real portfolio packaging. [Verification](verification.md) records the exact revision and distinguishes hosted, local and historical reproduction evidence.

## Run the raw baseline release separately

```powershell
.\.venv\Scripts\python.exe drivecheck.py --config configs/m4-release.json --output-dir outputs/baseline-new
if ($LASTEXITCODE -ne 0) { throw 'Baseline release failed.' }
.\.venv\Scripts\python.exe -E -s -m tools.reproduce --verify-run outputs/baseline-new
if ($LASTEXITCODE -ne 0) { throw 'Baseline report audit failed.' }
```

This preserves the raw baseline's 76 main cases and five separate latency diagnostics. It does not combine their denominators. Its report entry is `report/report.html` under the chosen destination.

## Reproduce the core in a fresh source/package environment

```powershell
.\.venv\Scripts\python.exe -m tools.reproduce_c1
```

The wrapper copies an explicit 55-file core comparison inventory into a new workspace under `outputs/`, creates a new environment, installs the selected hash-checked wheels, runs the copied tests/lint and independently audits original/copied reports. It compares complete file inventories and preserves the original environment and runs. Failures retain their status and logs. Optional `--wheelhouse <project-local-cache>` reuses reviewed wheels instead of downloading them again.

This core snapshot has its own explicit test inventory; it is distinct from the full checkout tests and hosted portfolio build above. The separate raw-release wrapper is `python -E -s -m tools.reproduce` using the project interpreter. See [verification](verification.md) for the observed same-machine/new-environment proof and its scope.

## Interpret provenance and failures

- Source/configuration hashes identify exact bytes. Editing code or changing Git line endings can make an older report fail current-checkout provenance even if its numerical results remain meaningful. Preserve the old run and regenerate from the current checkout; do not rewrite its hashes or weaken the audit.
- A successful command must produce the expected complete manifest and case inventory. Existing files alone do not establish success, and failed/partial methods are not zero-error successes.
- Repeated byte-identical files verify reproducibility for those inputs. They do not add holdout cases, establish statistical significance or prove cross-machine/pixel identity.
- Package installation may need network access. Installed CPU experiments and local reports use no external resources. Browser-rendered layout has not been included in the recorded static checks.
- Generated runs, environments and wheel caches remain under ignored `outputs/` and `.venv/`; they are not required source-repository contents.
