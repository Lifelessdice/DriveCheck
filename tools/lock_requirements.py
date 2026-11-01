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
                name
                for name in archive.namelist()
                if name.endswith(".dist-info/METADATA") and len(name.split("/")) == 2
            ]
            if len(metadata_names) != 1:
                raise ValueError(f"expected one METADATA file: {wheel.name}")
            metadata = Parser().parsestr(
                archive.read(metadata_names[0]).decode("utf-8"),
                headersonly=True,
            )
        if (
            len(metadata.get_all("Name", [])) != 1
            or len(metadata.get_all("Version", [])) != 1
        ):
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
