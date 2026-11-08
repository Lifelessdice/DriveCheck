# Third-party software and sources

The [project MIT licence](LICENSE) applies to original DriveCheck source. It does not replace dependency, bundled-library or font notices.

## What this repository distributes

The intended source release contains DriveCheck's original Python source, tests, small synthetic configurations, dependency/version/hash records, documentation and the optional source for generating a local demonstration. It does not vendor the Python interpreter, installed packages, wheel cache, font files, an environment or an external dataset. Generated local reports and demonstration folders remain under ignored `outputs/` by default. The figures are generated from the project's synthetic experiments, not copied from a third-party publication.

The table below is an inventory of the **selected dependency releases**, not a statement that all components are licensed under MIT or that licence labels alone establish redistribution compliance. Exact selected wheel hashes are in [requirements-lock.txt](requirements-lock.txt); the twelve runtime version pins are in [requirements.txt](requirements.txt). Pip and Ruff are additional tooling pins. The recorded target is CPython 3.14.7 / Windows x64.

## Selected dependencies and their upstream notices

Licence-file paths below are relative to an installation's `Lib/site-packages/`. They identify the exact installed notices inspected locally without publishing an absolute machine path. The retained original environment contains the runtime set and pip; Ruff's installed notice was inspected in the accepted C1 reproduction environment. That reproduction checked all fourteen selected package versions.

| Distribution | Version | Licence observed in selected metadata/text | Installed notice location and upstream release |
| --- | --- | --- | --- |
| contourpy | 1.4.0 | BSD-3-Clause | `contourpy-1.4.0.dist-info/licenses/LICENSE`; [release](https://pypi.org/project/contourpy/1.4.0/) |
| cycler | 0.12.1 | BSD-3-Clause-style terms, copyright matplotlib project | `cycler-0.12.1.dist-info/LICENSE`; [release](https://pypi.org/project/cycler/0.12.1/) |
| fonttools | 4.67.0 | MIT for the main software; separate external font notices | `fonttools-4.67.0.dist-info/licenses/LICENSE` and `LICENSE.external`; [release](https://pypi.org/project/fonttools/4.67.0/) |
| kiwisolver | 1.5.1 | Modified BSD / BSD-3-Clause terms | `kiwisolver-1.5.1.dist-info/licenses/LICENSE`; [release](https://pypi.org/project/kiwisolver/1.5.1/) |
| matplotlib | 3.11.2 | Matplotlib licence agreement, with separately licensed bundled material | `matplotlib-3.11.2.dist-info/LICENSE`; [release](https://pypi.org/project/matplotlib/3.11.2/) |
| numpy | 2.5.4 | `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` in metadata; additional component notices retained in the wheel | `numpy-2.5.4.dist-info/licenses/LICENSE.txt` and the full `licenses/numpy/` tree; [release](https://pypi.org/project/numpy/2.5.4/) |
| packaging | 26.3 | `Apache-2.0 OR BSD-2-Clause` | `packaging-26.3.dist-info/licenses/LICENSE`, `LICENSE.APACHE`, `LICENSE.BSD`; [release](https://pypi.org/project/packaging/26.3/) |
| pillow | 13.0.0 | MIT-CMU; preserve the selected distribution's full notices for any bundled components | `pillow-13.0.0.dist-info/licenses/LICENSE`; [release](https://pypi.org/project/pillow/13.0.0/) |
| pyparsing | 3.3.3 | MIT | `pyparsing-3.3.3.dist-info/licenses/LICENSE`; [release](https://pypi.org/project/pyparsing/3.3.3/) |
| python-dateutil | 3.0.0 | Apache-2.0 and BSD terms applying as described in its licence text | `python_dateutil-3.0.0.dist-info/licenses/LICENSE`; [release](https://pypi.org/project/python-dateutil/3.0.0/) |
| six | 1.17.0 | MIT | `six-1.17.0.dist-info/LICENSE`; [release](https://pypi.org/project/six/1.17.0/) |
| tzdata | 2026.5 | Apache-2.0 package text; retain time-zone data notices in the selected distribution | `tzdata-2026.5.dist-info/licenses/LICENSE` and `licenses/LICENSE_APACHE`; [release](https://pypi.org/project/tzdata/2026.5/) |
| pip — installation tooling | 26.2.1 | MIT for pip; vendored dependencies have their own licences | `pip-26.2.1.dist-info/licenses/LICENSE.txt`, `AUTHORS.txt` and the complete `licenses/src/pip/_vendor/` tree; [release](https://pypi.org/project/pip/26.2.1/) |
| ruff — lint tooling | 0.14.0 | MIT | `ruff-0.14.0.dist-info/licenses/LICENSE`; [release](https://pypi.org/project/ruff/0.14.0/) |

Matplotlib renders the plots; Pillow verifies PNG artifacts. The motion, observation, causal replay, warning and scoring implementation uses Python's standard library. The other runtime entries are the resolved plotting dependency set, not a claim that the model requires a separate numerical-estimation framework.

The interpreter is a separate prerequisite rather than a bundled part of this source release. Python's own licence and incorporated-software notices remain applicable to Python; see the [official Python licence documentation](https://docs.python.org/3.14/license.html).

## Bundled components and fonts

Short package labels omit details that matter if an installed distribution is copied or repackaged. The selected wheels retain their upstream notices; this repository does not strip or replace them.

- Matplotlib includes font notices at `matplotlib/mpl-data/fonts/ttf/LICENSE_DEJAVU` and `LICENSE_STIX`. The inspected DejaVu notice identifies Bitstream Vera, public-domain DejaVu changes and Arev contributions; the STIX notice describes the bundled font conversion and original font terms. The local demo uses rendered plot PNGs and does not distribute the font binaries.
- FontTools' `LICENSE.external` identifies test-font projects under SIL Open Font License 1.1. Those font projects and their reserved-name terms are separate from the main MIT software licence; no such test-font collection is copied into DriveCheck.
- NumPy's installed `licenses/` tree includes notices for libdivide, pythoncapi-compat, highway, Dragon4, x86-simd-sort, SVML, pocketfft, LAPACK-lite, masked arrays and random-generator components. The selected Windows wheel's main licence text also identifies OpenBLAS under BSD-3-Clause and its bundled LAPACK under BSD-3-Clause-Open-MPI. The full selected wheel, not just this summary, is the record for those components.
- Pillow's installed licence file includes bundled notices beyond its main MIT-CMU terms, including Brotli and FreeType. Those texts remain part of the selected distribution; the one-line package identifier does not replace them.
- Pip retains licences for its vendored packages, including cachecontrol, certifi, distlib, distro, idna, msgpack, packaging, pkg_resources, platformdirs, pygments, pyproject-hooks, requests, resolvelib, rich, tomli, tomli-w, truststore and urllib3. Pip itself is not redistributed with the portfolio source.

If a later release bundles wheels, installed packages, interpreter files or font assets, its release review must include the complete applicable notices and distribution conditions from those exact artifacts. The present source-only inventory is not a blanket clearance for a different binary bundle.

## Technical references and original synthetic data

The following references support the equations and API behaviour. Conceptual references are distinguished from copied implementation:

- [OpenStax University Physics Volume 1, §3.4: Motion with Constant Acceleration](https://openstax.org/books/university-physics-volume-1/pages/3-4-motion-with-constant-acceleration) supports the position/velocity and displacement reasoning. DriveCheck defines its own bumper coordinates, phase boundaries, stopping rule and finite evaluation horizon. The project does not reproduce an OpenStax figure or a block of textbook prose.
- [Eclipse SUMO SSM Device: TTC](https://sumo.dlr.de/docs/Simulation/Output/SSM_Device.html#ttc) supports the following-vehicle gap/closing-speed TTC interpretation. No SUMO implementation is copied into the warning rule. This reference does not establish a universal warning threshold or safety certification.
- [Python's official documentation](https://docs.python.org/3.14/) supports the standard-library APIs, isolated-environment instructions and test runner used in the project. [Matplotlib documentation](https://matplotlib.org/stable/) supports local file plotting. API documentation is cited as documentation, not presented as independently authored project theory.

The scenario/reference fixtures and fault streams are synthetic. There is no imported real-road dataset, employer data, vehicle log, CARLA recording or third-party branding asset in the intended portfolio package. The complete research and implementation decisions are in [docs/research.md](docs/research.md).
