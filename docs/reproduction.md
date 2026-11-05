# Reproduce the M4 CPU release

## M5 portfolio package — local checks, 5 November 2026

The [portfolio README](../README.md), [architecture](architecture.md), [results](results.md), [short demo script](demo.md) and [release review](release-review.md) describe the completed local M5 delivery. From an existing prepared checkout:

```powershell
.\.venv\Scripts\python.exe c1_compare.py --config configs/c1-comparison.json --output-dir outputs/c1-portfolio-new
if ($LASTEXITCODE -ne 0) { throw 'Comparison failed.' }
.\.venv\Scripts\python.exe -m tools.portfolio_demo --run outputs/c1-portfolio-new --output-dir outputs/portfolio-new
if ($LASTEXITCODE -ne 0) { throw 'Portfolio packaging or source audit failed.' }
Invoke-Item -LiteralPath .\outputs\portfolio-new\index.html
```

Both destinations must be fresh. The packager invokes the independent C1 auditor, binds the fixed narrative to the default configuration/plot selection/outcomes, copies all evidence without changing it and writes an offline presentation with a hash manifest. It adds no dependency or alternative algorithm. Five focused preservation/narrative tests and the complete **227-test suite** pass; Ruff passes. The full-suite observed time was 77.307 s, not a performance benchmark.

The M5 current-checkout comparison is `outputs/m5-c1-20261105`; two packages at `outputs/m5-portfolio-20261105` and `outputs/m5-portfolio-repeat-20261105` each have 1,426 byte-identical files. Their 1,424-file evidence copies match the source. All 629 CSVs and the numerical summary match the earlier accepted C1 report. Static QA checks two HTML pages, 1,114 contained links and three valid PNGs, without external HTML resources or scripts. Browser-rendered layout remains unverified because the local-file preview was blocked by browser security policy.

Byte provenance is strict. Nine historical C1 source inputs use LF where the current checkout uses CRLF; normalized content and all eight affected Python ASTs are equal, but their byte hashes differ. The historical proof below remains valid for its original source snapshot. Regenerate a report from the current checkout rather than changing its old hashes or weakening the audit. No core algorithm/configuration was changed for M5.

The commands below retain their original revision-specific evidence. No fresh environment was created for M5; the accepted C1 new-environment proof remains separate from the new current-checkout package checks.

Hosted C1 verification, 5 November 2026: [run 42011728510](https://github.com/Lifelessdice/DriveCheck/actions/runs/42011728510) passed at `b293a5b8089c373fb440130d013450a2963f2745`. All 222 tests passed in 33.159 s, dependency consistency and Ruff passed, and both complete M4 and C1 reports were generated and independently audited. C1 retained 157 pairs / 314 method records, 3,302 decision rows, 1,418 machine hashes, four report hashes and 1,102 contained links. The assistant performed the explicitly requested push; this does not establish learner mastery. The local byte-identity proof below remains separate from hosted execution.

## C1 reproduction — verified 4 November 2026

The completed comparison has its own wrapper; the M4 commands below remain usable:

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe -m tools.reproduce_c1
```

Optional `--wheelhouse <project-local-cache>` reuses reviewed wheels. The wrapper preserves the original environment and runs. It copies 55 explicit inputs, creates a new environment, installs the existing 14-package hash lock, checks dependencies/lint, runs the full suite, generates original/copied comparison reports and independently audits both. It rejects a differing file inventory or source changes during reproduction.

Observed proof at code revision `163aab5`: `outputs/c1-reproduction-6c4f270cbbe5428b94d559633e551ed6/reproduction.json` is complete. All 222 copied-source tests pass in 88.287 s, pip consistency and Ruff pass, all 55 input hashes and 14 wheel/package pins match, and both 1,424-file reports are byte-identical. Each report retains 76 development pairs, 76 evaluation pairs and five separate diagnostics, 314 method records, 3,302 checked decision rows, 1,418 machine hashes, three inspected PNGs and 1,102 contained local links. The recorded target is CPython 3.14.7 / Windows x64; this is same-machine/new-environment proof.

For a report without a new environment:

```powershell
.\.venv\Scripts\python.exe c1_compare.py --config configs/c1-comparison.json --output-dir outputs/c1-example
.\.venv\Scripts\python.exe -m tools.verify_c1 outputs/c1-example
```

Choose a fresh directory; open its `report/report.html`. The [investigation](c1-investigation.md) records all wins, losses, unchanged cases and limits. Hosted C1 verification is linked above. The older M4 evidence below remains revision-specific historical proof.

Hosted verification, 1 November 2026: [run 41260971755](https://github.com/Lifelessdice/DriveCheck/actions/runs/41260971755) succeeded for code commit `e64b12baf4a4ba5e93a91e2b40541bb7c5df6ed4`. All 169 tests passed in 18.010 s, together with dependency/lint checks and full release generation/audit. The audited report has 76 main cases plus five separate diagnostics, 343 machine hashes, 356 package hashes, 357 files, 11 plots and 421 links. Byte-for-byte comparison below refers to the two local reports; cross-machine pixel identity is untested. The assistant performed the explicitly approved commit/push; work remains on the M4 branch.

The supported lock target is **CPython 3.14.7 on Windows x64**. The runtime versions remain in `requirements.txt`; `requirements-lock.txt` binds all 12 runtime packages plus pip26.2.1 and Ruff0.14.0 to the selected wheel bytes. This is a platform-specific lock.

`.gitattributes` keeps the generated lock's LF line endings on checkout, so Windows Git conversion cannot make the helper mistake the same lock for different content. The copied execution snapshot contains 42 inputs; Git checkout policy is applied before that snapshot is made.

## One command in the existing project environment

From the project folder:

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe -E -s -m tools.reproduce
```

The command downloads the selected wheels from PyPI, checks the existing lock, creates a new environment under an automatically unique `outputs/m4-environment/reproduction-<id>` folder and installs only the local hash-checked wheels. It preserves the original environment and earlier runs. With `--wheelhouse <directory>`, it reuses previously downloaded wheels and requires no package download for that run.

It copies an explicit 42-file source/configuration/tooling/workflow inventory, verifies every copy, runs lint and the full tests, then generates the full release in both the original environment and the new environment/copy. Python import overrides and user-site packages are excluded from the subprocesses. Copied-source lint explicitly bypasses the parent repository's ignored `outputs/` path.

Each subprocess has its own log. The final `reproduction.json` records status, both report audits, input and wheel hashes, and any differing output paths. Failures return nonzero and retain a failed record. No previous folder is overwritten or deleted. The original environment must already contain the recorded runtime packages so its baseline tests/report can run.

## Bootstrap a genuinely new checkout

Install the exact CPython3.14.7 Windows x64 interpreter first. In a new checkout without an existing `.venv`, run this block, then use the reproduction command above:

```powershell
& {
    if (Test-Path -LiteralPath '.venv') {
        throw 'An environment already exists; use the existing-project instructions.'
    }
    py -3.14 -c "import platform, struct, sys; expected = platform.python_implementation() == 'CPython' and sys.version_info[:3] == (3, 14, 7) and sys.platform == 'win32' and struct.calcsize('P') == 8 and platform.machine().lower() in {'amd64', 'x86_64'}; sys.exit(0 if expected else 'Expected CPython 3.14.7 / Windows x64')"
    if ($LASTEXITCODE -ne 0) { throw 'Interpreter check failed' }
    py -3.14 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Environment creation failed' }
    .\.venv\Scripts\python.exe -E -s -m pip --isolated install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: --force-reinstall -r requirements-lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Hash-locked installation failed' }
}
```

The exact runtime check prevents a different installed 3.14 patch from silently changing the target. The bootstrap recipe is documented; the actually observed local proof below used the retained original environment and a newly created environment. GitHub CI independently exercises a fresh hosted checkout.

## Audit an individual full release

```powershell
.\.venv\Scripts\python.exe -E -s -m tools.reproduce --verify-run outputs/ci-release
```

Replace the argument with a generated full-release directory under this checkout's `outputs/`. This audit intentionally requires the default 76-main/five-diagnostic configuration and matching current-checkout source/configuration provenance. Historical reports remain preserved; use their corresponding source revision when requesting this stronger audit.

The auditor reuses the machine-data validator, checks completed package status, complete machine/package file inventories, exact hashes, predeclared plot IDs and PNG files, and all contained report links. It rejects extra unlisted files as well as damaged listed files. It verifies source/configuration hashes against the checkout running the audit. Main and diagnostic results retain separate denominators.

## Observed local evidence — 1 November 2026

At my request, the assistant completed the remaining environment/lint/reproduction setup and authored the reusable wrapper and CI workflow. This is assistant implementation/verification under explicit delegation, separate from my independent understanding.

- Six focused lock tests pass. The generated 14-package lock matches every wheel's identity, version and SHA-256; installed versions and dependency consistency were checked.
- Ruff passes after adding the intended exclusions and removing four unused imports. The preserved scratch/editor files and original environment were retained.
- The original-environment full suite passes 169 tests in 21.173 s; the copied-source/new-environment suite passes 169 tests in 19.545 s. These are test timings, not a benchmark or learner focused-time estimate.
- Both regenerated reports complete 76 main cases plus five separate diagnostics. Each has 343 machine hashes, 356 package hashes, 357 files, 11 plots and 421 contained existing local references. All 357 files are byte-identical.
- The 42 copied input hashes and 14 wheel hashes are retained in the reproduction record. The 11 PNG hashes match the figures individually inspected at the preceding report checkpoint. Browser-rendered layout remains unverified.
- Three separate negative controls return exit1: a modified decision CSV, an extra unlisted file and a partial package status. They use copies; accepted evidence is preserved.

The local evidence folder is `outputs/m4-environment/reproduction-a333f2ee32424d88932841845026961c`, which is ignored by Git. The public repository contains the commands/configuration/code, not this local environment or wheelhouse.

This proves clean-source/new-package-environment reproduction on this machine. CI uses the same pinned Python/package target on a hosted Windows image; it does not promise an immutable entire OS or pixel-identical results across different platforms. Warnings remain passive synthetic experiments, with no real-vehicle safety claim.
