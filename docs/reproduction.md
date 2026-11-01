# Reproduce the M4 CPU release

The supported lock target is **CPython 3.14.7 on Windows x64**. The runtime versions remain in `requirements.txt`; `requirements-lock.txt` binds all 12 runtime packages plus pip26.2.1 and Ruff0.14.0 to the selected wheel bytes. This is a platform-specific lock.

`.gitattributes` keeps the generated lock's LF line endings on checkout, so Windows Git conversion cannot make the helper mistake the same lock for different content. The copied execution snapshot contains42inputs; Git checkout policy is applied before that snapshot is made.

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

- Six focused lock tests pass. The generated14-package lock matches every wheel's identity/version/SHA-256; installed versions and dependency consistency were checked.
- Ruff passes after adding the intended exclusions and removing four unused imports. The preserved scratch/editor files and original environment were retained.
- The original-environment full suite passes169tests in21.173s; the copied-source/new-environment suite passes169tests in19.545s. These are test timings, not a benchmark or learner focused-time estimate.
- Both regenerated reports complete76main cases plus five separate diagnostics. Each has343machine hashes,356package hashes,357files,11plots and421contained existing local references. All357files are byte-identical.
- The42copied input hashes and14wheel hashes are retained in the reproduction record. The11PNG hashes match the figures individually inspected at the preceding report checkpoint. Browser-rendered layout remains unverified.
- Three separate negative controls return exit1: a modified decision CSV, an extra unlisted file and a partial package status. They use copies; accepted evidence is preserved.

The local evidence folder is `outputs/m4-environment/reproduction-a333f2ee32424d88932841845026961c`, which is ignored by Git. The public repository contains the commands/configuration/code, not this local environment or wheelhouse.

This proves clean-source/new-package-environment reproduction on this machine. CI uses the same pinned Python/package target on a hosted Windows image; it does not promise an immutable entire OS or pixel-identical results across different platforms. Warnings remain passive synthetic experiments, with no real-vehicle safety claim.
