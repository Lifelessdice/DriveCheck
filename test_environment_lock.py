"""Check lock identity, exact-byte hashes and preservation guards."""

import hashlib
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from tools.lock_requirements import ROOT, TOOL_PINS, build_lock, save_lock


class EnvironmentLockTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "outputs").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.requirements = self.root / "requirements.txt"
        self.requirements.write_text("Example_pkg==1.2\n", encoding="utf-8")
        self.wheels = self.root / "wheels"
        self.wheels.mkdir()
        self.example = self.wheel("Example.pkg", "1.2", "example.whl")
        for name, version in TOOL_PINS.items():
            self.wheel(name, version, f"{name}.whl")

    def wheel(self, name, version, filename):
        path = self.wheels / filename
        with ZipFile(path, "w") as archive:
            archive.writestr(
                "package.dist-info/METADATA",
                f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n\n",
            )
        return path

    def test_metadata_identity_and_actual_byte_hash(self):
        result = build_lock(self.requirements, self.wheels)
        digest = hashlib.sha256(self.example.read_bytes()).hexdigest()
        self.assertIn(f"example-pkg==1.2 --hash=sha256:{digest}\n", result)
        pins = [line for line in result.splitlines() if not line.startswith("#")]
        self.assertEqual(len(pins), 3)
        self.assertEqual(pins, sorted(pins))
        self.assertEqual(result, build_lock(self.requirements, self.wheels))

    def test_missing_wheel(self):
        self.example.unlink()
        with self.assertRaisesRegex(ValueError, "missing wheels"):
            build_lock(self.requirements, self.wheels)

    def test_duplicate_normalized_identity(self):
        self.wheel("example-pkg", "1.2", "duplicate.whl")
        with self.assertRaisesRegex(ValueError, "duplicate wheel"):
            build_lock(self.requirements, self.wheels)

    def test_wrong_version(self):
        self.wheel("example-pkg", "9.9", "example.whl")
        with self.assertRaisesRegex(ValueError, "wrong version"):
            build_lock(self.requirements, self.wheels)

    def test_unexpected_package(self):
        self.wheel("unplanned", "1.0", "unplanned.whl")
        with self.assertRaisesRegex(ValueError, "unexpected package"):
            build_lock(self.requirements, self.wheels)

    def test_identical_lock_allowed_but_different_content_preserved(self):
        path = self.root / "requirements-lock.txt"
        save_lock(path, "first\n")
        save_lock(path, "first\n")
        with self.assertRaisesRegex(ValueError, "different lock"):
            save_lock(path, "second\n")
        self.assertEqual(path.read_bytes(), b"first\n")


if __name__ == "__main__":
    unittest.main()
