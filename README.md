# DriveCheck

I am building a Python workbench to investigate how sensor quality affects a simple collision-warning algorithm. My current learning checkpoint is **M1, in progress**. My reviewed work includes the constant-speed gap calculation, guided five-row console table and first saved CSV.

I work in the original project files and implement/run the changes myself. My assistant prepares the explanations, guided code, tests and study documents. Earlier assistant-created M1 implementation/artifacts have been archived locally; they are separate from my active code and learning evidence.

## Continue M1

Start with [the M1 lesson](docs/lessons/m1-clean-movement.md), using `motion.py` and `test_motion.py`. The complete curriculum is indexed in [the study guide](docs/study-guide.md). No duplicate practice implementation or environment restart is required.

`motion.py` contains my original gap function, a reusable constant-speed sampler and the manual console table. Following the supplied lesson, I corrected the elapsed-time spelling and added finite/type/count validation and four sampler tests. My assistant reviewed the saved changes and ran all five tests successfully, including the unchanged original known-answer fixture. My nine-sample half-second test remains a transfer exercise; this review does not establish independent conceptual understanding.

## Run the existing baseline

Use the existing project environment from PowerShell:

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe .\motion.py
.\.venv\Scripts\python.exe -m unittest -v test_motion
```

The console table is:

```text
time_s,gap_m
0.0,30.0
1.0,25.0
2.0,20.0
3.0,15.0
4.0,10.0
```

Both vehicles move forward on the same axis. Bumper gap is the distance from the ego front to the lead rear. The ego travels at 20 m/s and the lead at 15 m/s, so the original 30 m gap decreases by 5 m each second. After two seconds, separate travel distances give `30 + 30 - 40 = 20 m`, the fixed answer in the original test.

Five samples at one-second spacing span four seconds because the initial state is included. My first `outputs/constant_speed.csv` snapshot is preserved. Generated outputs are ignored by Git.

## Current limits and attribution

The supplied sampler tests pass; my changed-count transfer test/explanation, a clean-data contract, braking/contact/non-contact fixtures and labelled plots remain M1 learning work. Sensor observations, fault injection, warnings and evaluation belong to later milestones. A ready lesson or historical assistant test run does not establish my independent implementation or understanding.

The existing environment uses Python 3.14.7. Plotting dependencies installed during the earlier assistant reference work remain in that environment; the current baseline needs only the standard library. See [research and historical dependency decisions](docs/research.md). Fresh-environment/remote CI evidence remains later work.

I completed the original calculation, guided loop and first known-answer test with AI-assisted teaching/templates. Assistant implementation beyond that was archived when I chose to resume building from my original code. This is an offline simplified model, with no real-vehicle control or safety-validation claim. No Git/publication result is claimed.
