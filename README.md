# DriveCheck

I am building a Python workbench to investigate how sensor quality affects a simple collision-warning algorithm. My current learning checkpoint is **M1, in progress**. My reviewed work includes the constant-speed gap calculation, guided five-row console table and first saved CSV.

I work in the original project files and implement/run the changes myself. My assistant prepares the explanations, guided code, tests and study documents. Earlier assistant-created M1 implementation/artifacts have been archived locally; they are separate from my active code and learning evidence.

## Continue M1

Start with [the M1 lesson](docs/lessons/m1-clean-movement.md), using `motion.py` and `test_motion.py`. The complete curriculum is indexed in [the study guide](docs/study-guide.md). No duplicate practice implementation or environment restart is required.

`motion.py` contains my original gap function, a constant-speed sampler, immutable scenario/truth records and a lead-braking state evaluator with rich sampling. Following the supplied lessons, I added the records, functions and known-answer tests. My assistant corrected the braking duration/travel calculation and missing test import at my request, then ran all thirteen tests successfully. The checks include the original fixture, changed timestep/horizon, braking values and a lead vehicle that remains stopped. This is guided implementation with assistant verification; it does not establish my independent conceptual understanding.

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

The supplied sampler, records and braking checks pass. Exact continuous contact events, independently checked non-contact cases, full CSV/configuration export and labelled plots remain M1 work, alongside my explanation/transfer review. Negative gaps are virtual overlap of prescribed paths, with no impact response simulated. Sensor observations, fault injection, warnings and evaluation belong to later milestones. Passing supplied tests does not establish independent implementation or understanding.

The existing environment uses Python 3.14.7. Plotting dependencies installed during the earlier assistant reference work remain in that environment; the current baseline needs only the standard library. See [research and historical dependency decisions](docs/research.md). Fresh-environment/remote CI evidence remains later work.

I completed the original calculation, guided loop and first known-answer test with AI-assisted teaching/templates. The earlier assistant-created full M1 reference was archived when I chose to build in the original files; current lessons and targeted assistant fixes are attributed separately. A private GitHub repository is connected; no remote CI result is claimed. This is an offline simplified model, with no real-vehicle control or safety-validation claim.
