# Verification

Recorded target: **CPython 3.14.7 / Windows x64**, with the selected runtime and tooling artifacts pinned in [requirements-lock.txt](../requirements-lock.txt). Results below belong to the named revisions and runs; a historical pass is not a new check of a later change.

## Hosted checks

The documentation cleanup also passed [main CI run 42481018862](https://github.com/Lifelessdice/DriveCheck/actions/runs/42481018862) at `d4c070c5fbc601d7f8698829532ff1bf7c7d2ab6` on 8 November 2026: **227 tests in 27.992 s**, dependency/Ruff checks, both complete experiment audits and the real portfolio build. This precedes the export adapter checks described below.

[Main CI run 42056296813](https://github.com/Lifelessdice/DriveCheck/actions/runs/42056296813) succeeded at revision `b2168f189377c9b7919f289f81f1b6e986b973ef` on 5 November 2026.

| Check | Observed result |
| --- | --- |
| Unit and integration suite | **227 tests passed in 33.920 s** |
| Environment and lint | Dependency consistency and pinned Ruff checks passed |
| Full CPU release | All 76 main cases and five separate diagnostics generated and passed the report audit |
| Paired comparison | All 157 pairs / 314 method records completed; the audit checked 3,302 decision rows against saved inputs, causal selection, estimates and scoring |
| Portfolio demo | The real packager completed after the comparison audit, preserving all 1,424 evidence files; entry HTML and the separate manifest make 1,426 total files |

The [workflow](../.github/workflows/ci.yml) uses an isolated environment, the exact Python/package target, read-only repository permissions and explicit failure checks. It runs the full experiment and portfolio build rather than checking only that their modules import.

## What the tests and audits establish

- **Independent model and metric answers.** Analytic fixtures check braking/contact, non-contact, stop-and-go and horizon boundaries. Metric fixtures distinguish useful, late, missed and false-warning episodes using expected answers defined separately from the TTC rule. See [model tests](../test_motion.py), [scenario tests](../test_m3_scenarios.py) and [evaluation tests](../test_evaluation.py).
- **Causal decisions.** Replay tests cover availability, arrival ordering, source age, stale/unavailable data and boundary decisions. Causal-prefix checks confirm that later arrivals cannot change earlier decisions. Raw and projected methods share the queue, freshness gate, TTC branches and scoring policy. See [replay tests](../test_replay.py) and [comparison replay tests](../test_c1_replay.py).
- **Complete, inspectable evidence.** [The C1 auditor](../tools/verify_c1.py) checks inventory and hashes, then reconstructs the physical/reference/fault arithmetic, source selection, used state, decisions, scores and aligned errors. A wrong CSV does not become valid merely by updating its hash. [Audit tests](../test_c1_audit.py) include tampering, omitted evidence, incomplete status and changed-report controls.
- **Preserving portfolio export.** [The packager tests](../test_portfolio_demo.py) check rejection of existing destinations and invalid evidence, unchanged source/copy bytes, and rejection of plot selections or outcomes that do not support the fixed narrative. [The packager](../tools/portfolio_demo.py) retains the complete report beneath the short presentation.

These checks support the documented behaviour and fixed experiment. They do not prove correctness for every possible input or establish real-world warning safety.

## Local repeatability

The recorded local portfolio check on 5 November passed all **227 tests in 77.307 s** and Ruff. Two independently created packages each contained **1,426 files with zero byte differences**, including the identity manifests. Each package's 1,424-file evidence copy matched its source run without changing it.

The regenerated comparison also preserved **all 629 CSV files** and the complete numerical summary from the earlier accepted comparison. Source/provenance bytes can differ between revisions or checkout line endings; this numeric/data comparison is distinct from claiming that whole reports from different source snapshots have identical provenance.

Static demo checks covered two HTML pages, **1,114 contained local links**, no scripts or external HTML resources, and three valid 1200×1200 PNGs. The plots were visually inspected. **Browser-rendered layout and network-disconnected browser behaviour remain unverified.** Static link/image checks are the scope of the recorded HTML validation.

## Copied-source, new-environment reproduction

The earlier comparison reproduction at code revision `163aab5` remains a separate result. [The reproduction tool](../tools/reproduce_c1.py) copied an explicit source inventory, created a new environment and installed the selected fourteen hash-locked package artifacts. Dependency checks and Ruff passed, and the copied environment passed **222 tests in 88.287 s**. The original and copied runs each contained **1,424 files, with zero differences**.

That proof is same-machine/new-environment reproduction on the recorded Windows/Python target. It predates the portfolio tests and is not presented as a fresh-environment run of the later 227-test revision. Hosted execution above supplies separate evidence for that later revision; cross-platform or cross-machine pixel identity is not established.

A separate raw-baseline compatibility check matched **243 truth, observation and raw-decision files across 81 baseline cases**, byte for byte. This checks preservation of the usable baseline beyond agreement of summary metrics.

## CPU export adapter checks

The adapter suite covers literal and rotated geometry, timing, input validation, independent collision labels, replay and failure retention. On Windows x64 with CPython 3.14.7, 54 of 55 adapter tests passed and one was skipped because the local environment could not create a symbolic link. Ruff passed. The workflow also runs both fixtures through the CLI.

The local contact and non-contact runs each produced 16 files. Checks covered the 15 payload hashes, source and configuration bytes, frame mapping, scores, 15 local HTML resource references and a valid PNG. The contact replay produced 16 byte-identical files on a second run in the same environment. Plot inspection covered the expected warning times. These checks use hand-authored exports. Real simulator capture remains unverified. [Adapter commands and expected outcomes](carla-import.md)

## Reproduce and inspect

Use the exact setup and fresh-output commands in [reproduction.md](reproduction.md). The comparison command generates the complete case inventory, configuration, traces and report; `tools.verify_c1` audits that saved run. The [demo instructions](demo.md) package it without replacing the underlying evidence. Hash verification uses the recorded source bytes, so an older run should be checked with its corresponding source snapshot or regenerated from the current checkout.

The [architecture](architecture.md) defines the data/timing/scoring contracts. The [results](results.md) and [investigation](c1-investigation.md) explain the measured trade-off, denominators and finite-horizon limitations. Recorded test durations are execution evidence, not a performance benchmark.
