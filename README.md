# DriveCheck

I am building a Python workbench to investigate how sensor quality affects a simple collision-warning algorithm. **The M1 clean-motion implementation is verified; my final explanation and changed-input review remain pending.** The active project generates checked truth data, configuration and labelled plots for three study cases.

I work in the original project files and implement/run the changes myself. My assistant prepares the explanations, guided code, tests and study documents. Earlier assistant-created M1 implementation/artifacts have been archived locally; they are separate from my active code and learning evidence.

## Continue M1

Start with [the M1 lesson](docs/lessons/m1-clean-movement.md), using `motion.py` and `test_motion.py`. The complete curriculum is indexed in [the study guide](docs/study-guide.md). No duplicate practice implementation or environment restart is required.

`motion.py` contains my original gap function, constant-speed and lead-braking trajectories, immutable scenario/truth records and analytic contact-event detection. `scenarios.py` pairs each case with independently specified reference values. `m1.py` checks those values and exports full truth CSVs, JSON configuration/provenance and PNG plots, with artifact hashes in a run manifest. Following the supplied lessons, I added these modules and tests, with targeted assistant fixes/review.

On 28 October 2026 my assistant ran all **24 tests successfully**, verified my saved study outputs against their configuration, source and artifact hashes, and visually inspected all three plots. Integration tests also check a failed reference, rejected output destinations and repeated exports with identical hashes on this machine. This is guided implementation with assistant verification; my explanation and independent transfer remain separate learning evidence.

The braking contact fixture has an independently calculated event at `sqrt(11) = 3.3166247903554 s`, between its saved 3 s and 4 s rows. A separate fixture remains non-contact through 8 s but contacts at 10 s if extended. Contact labels therefore apply to the declared horizon. Phase endpoint rounding uses 32 ULPs of the actual endpoint time scale.

## Run the existing baseline

Use the existing project environment from PowerShell:

```powershell
Set-Location 'E:\DriveCheck'
.\.venv\Scripts\python.exe .\motion.py
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe .\m1.py
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

The M1 command writes three CSV/JSON/PNG sets and `manifest.json` to `outputs/m1-study/`:

| Case | Rows | Horizon | First contact within horizon | Final gap |
| --- | ---: | ---: | ---: | ---: |
| `constant_speed_original` | 5 | 4 s | None | 10 m |
| `lead_braking_contact` | 6 | 5 s | 3.3166247903554 s | -32.5 m |
| `lead_braking_noncontact` | 9 | 8 s | None | 20 m |

Each sidecar records SI units, bumper-axis/sign conventions, sampling/horizon rules, independent and computed answers, source/test/requirements hashes, installed versions and no randomness. A successful run has manifest status `complete` with matching artifact hashes; a failed run can leave older files in a reused folder, so file existence alone is insufficient.

## Current limits and attribution

The supplied trajectory, contact/non-contact and export checks pass. My final explanation/transfer review remains M1 work. Negative gaps are virtual overlap of prescribed paths, with no impact response simulated. Sensor observations, fault injection, warnings and evaluation belong to later milestones. Passing supplied tests does not establish independent implementation or understanding.

The existing environment uses Python 3.14.7. The motion model uses the standard library; export plots use the retained Matplotlib installation and PNG verification uses Pillow. `requirements.txt` records the 12 installed runtime dependency versions and was checked against the environment. It is a version snapshot, not a wheel-hash lock or fresh-environment reproduction result. See [research and historical dependency decisions](docs/research.md). Fresh-environment/remote CI evidence remains later work.

I completed the original calculation, guided loop and first known-answer test with AI-assisted teaching/templates. The earlier assistant-created full M1 reference was archived when I chose to build in the original files; current lessons and targeted assistant fixes are attributed separately. The GitHub repository is public; no remote CI result is claimed. This is an offline simplified model, with no real-vehicle control or safety-validation claim.
