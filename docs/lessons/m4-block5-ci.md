# M4 Block 5 — Run the CPU checks on a published revision

Configured 1 November 2026 under the user's explicit delegation of the remaining M4 environment/reproduction/CI work. The assistant authored `.github/workflows/ci.yml`; this document explains it. Configuration, local verification and an actual remote run are separate evidence. **Remote CI remains pending until the published revision runs and its result is inspected.** Git actions belong to the coordinating chat's explicitly authorized scope; this section author did not stage, commit, push or merge anything.

The workflow runs on pushes, pull requests and manual dispatch. Its only repository permission is `contents: read`. It creates an isolated environment in the fresh CI checkout and selects **CPython 3.14.7 / Windows x64**, matching the recorded local target and platform-specific wheel hashes. The user's existing local `.venv` is not recreated or modified by this workflow.

The check sequence is:

1. Verify the interpreter version/architecture and create the CI environment.
2. Install all 14 selected packages from `requirements-lock.txt`, with hashes, binary wheels and forced installation of the selected artifacts, including pip. Installation uses package-server access; CPU tests and report generation do not require network services.
3. Run `pip check`, the pinned Ruff configuration and the full unit/integration suite. The current expected full suite is 169 tests; record only the count actually observed in a run.
4. Run the full configured CPU workflow through `drivecheck.py`.
5. Run `python -E -s -m tools.reproduce --verify-run outputs/ci-release`. This reusable auditor uses the existing report validator to check 76 complete main cases, five separately summarized diagnostics, all saved machine/package hashes, 11 distinct predeclared plots and 421 contained existing local references. The coordinating chat implements/verifies this helper as part of the local reproduction workflow.

There is no deployment or report-artifact upload step. A case with an algorithmic miss can still be a complete execution; a missing result, failed export, bad hash or broken asset makes the check fail. Main and diagnostic policies/denominators remain separate.

## Reviewed action and runtime sources

The two action revisions were resolved through GitHub's public tag API and their pinned `action.yml` files were read on 1 November 2026:

| Action | Reviewed version | Immutable commit |
| --- | --- | --- |
| checkout | v6.1.0 | `d23441a48e516b6c34aea4fa41551a30e30af803` |
| setup-python | v6.3.0 | `ece7cb06caefa5fff74198d8649806c4678c61a1` |

The workflow pins commits rather than moving major tags. Both reviewed actions use Node 24. Their primary definitions are [checkout at the pinned revision](https://raw.githubusercontent.com/actions/checkout/d23441a48e516b6c34aea4fa41551a30e30af803/action.yml) and [setup-python at the pinned revision](https://raw.githubusercontent.com/actions/setup-python/ece7cb06caefa5fff74198d8649806c4678c61a1/action.yml).

The official Python runtime manifest lists the regular Windows x64 build for 3.14.7, with release `3.14.7-31064857500`. This confirms that the requested target is listed, not that a CI run has succeeded. [Official runtime manifest](https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json)

`windows-latest` is a moving hosted OS image. Exact package artifacts, interpreter version and action commits are selected, but this is not a claim of an immutable entire machine or identical rendered pixels across operating systems. Actual remote results must be tied to their checked commit.

## What to inspect after publication

Open the workflow run for the published commit. Confirm the requested Python target, successful hash-locked installation, dependency/lint checks, actual full-test count, full CPU command and final saved-evidence verification. A green older revision does not verify later edits. If any step fails, inspect its bounded error/log output and preserve the local reproducible configuration; do not weaken checks to claim success.

Local equivalent checks can establish local acceptance while remote CI is pending. They cannot demonstrate hosted-runner availability, remote package access or the service's workflow execution. Learner understanding remains separate from assistant-performed implementation and passing checks.
