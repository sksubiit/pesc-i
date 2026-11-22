"""Native-engine installation safety and deterministic executable selection."""

from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from scripts.install_stockfish import BINARY_SHA256, install_archive, sha256
from src.engine.stockfish_wrapper import stockfish_path


class StockfishInstallTests(unittest.TestCase):
    def test_bad_archive_cannot_replace_existing_executable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            destination = root / "engine"
            destination.mkdir()
            target = destination / "stockfish"
            target.write_bytes(b"existing engine")
            bad = root / "bad.tar.gz"
            bad.write_bytes(b"not the official release")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                install_archive(bad, destination)
            self.assertEqual(target.read_bytes(), b"existing engine")
            self.assertEqual(list(destination.iterdir()), [target])

    def test_default_ignores_system_path_but_explicit_override_works(self):
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder) / "stockfish"
            fake.write_text("not the project engine")
            with patch.dict(os.environ, {"PATH": folder, "STOCKFISH_PATH": ""}):
                resolved = Path(stockfish_path())
                self.assertEqual(
                    resolved, Path(__file__).resolve().parents[1] / "stockfish/stockfish"
                )
                self.assertNotEqual(resolved, fake)
            with patch.dict(os.environ, {"STOCKFISH_PATH": str(fake)}):
                self.assertEqual(stockfish_path(), str(fake))

    def test_installed_executable_matches_the_verified_release(self):
        binary = Path(__file__).resolve().parents[1] / "stockfish/stockfish"
        self.assertEqual(sha256(binary), BINARY_SHA256)
