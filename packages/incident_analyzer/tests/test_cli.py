"""Tests for scripts/analyze.py CLI script."""

import subprocess
import sys
import unittest
from pathlib import Path


class TestAnalyzeCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[3]
        cls.script_path = cls.repo_root / "scripts" / "analyze.py"
        cls.fixture_path = cls.repo_root / "data" / "raw" / "incidents-nexova.csv"

    def test_cli_execution_with_fixture(self):
        """Tests CLI produces code 0 and exact expected output lines."""
        cmd = [
            sys.executable,
            str(self.script_path),
            str(self.fixture_path),
            "--no-export",
        ]
        result = subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, f"CLI failed: {result.stderr}")
        stdout = result.stdout
        self.assertIn("NEXOVA — SUPPORT TICKET ANALYSIS", stdout)
        self.assertIn("TOTAL RECORDS IN FILE .......... 100", stdout)
        self.assertIn("Valid records ................ 96", stdout)
        self.assertIn("Invalid / incomplete .......... 4", stdout)
        self.assertIn("TECHNICAL", stdout)
        self.assertIn("Average score: 3.84 / 5.00", stdout)

    def test_cli_missing_file_error_code(self):
        """Tests CLI exits with non-zero code when file does not exist."""
        cmd = [
            sys.executable,
            str(self.script_path),
            "non_existent_file.csv",
            "--no-export",
        ]
        result = subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Error: File not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
