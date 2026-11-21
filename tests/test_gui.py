"""Display tests run on WSLg/X11; skip on headless systems."""

import gc
import tempfile
import threading
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

import chess
from src.gui.gui_tk import ChessGUI
from src.voice.commentator import Commentary
from src.voice.providers import ModelConfig


class GuiTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("No graphical display; use WSLg or xvfb-run.")
        self.temp = tempfile.TemporaryDirectory()
        self.settings_patch = patch(
            "src.gui.settings.SETTINGS_PATH", Path(self.temp.name) / "settings.json"
        )
        self.settings_patch.start()
        self.app = ChessGUI(self.root)
        self.app.think_time.set("0.1")
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)

    def tearDown(self):
        if hasattr(self, "app"):
            self.app.on_close()
            del self.root.report_callback_exception
            self.settings_patch.stop()
            # Destroyed Tk cycles must be collected on their owning thread.
            gc.collect()
            self.temp.cleanup()

    def pump_until(self, predicate, timeout=8):
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.root.update()
        self.assertTrue(predicate(), self.app.status.get())
        self.assertEqual(self.errors, [])

    def test_local_move_analysis_undo_and_flip(self):
        app = self.app
        app.mode.set("Local two-player")
        app.new_game()
        app.play_move(chess.Move.from_uci("e2e4"))
        self.pump_until(lambda: not app.busy)
        self.assertIsNotNone(app.last_analysis)
        self.assertNotIn("analyzing", app.eval_text.get())
        self.assertEqual(app.turn_text.get(), "Black to move")
        self.assertIn("e4", app.notes.get("1.0", "end"))
        app.undo()
        self.assertEqual(app.board.fen(), chess.STARTING_FEN)
        app.flip()
        for square in chess.SQUARES:
            x, y = app.xy(square)
            self.assertEqual(app.square_at(x + 32, y + 32), square)

    def test_play_black_engine_starts_and_undo_returns_player_turn(self):
        app = self.app
        app.side.set("Black")
        app.new_game()
        self.pump_until(lambda: len(app.board.move_stack) == 1 and not app.busy)
        self.assertTrue(app.human_turn())
        move = next(iter(app.board.legal_moves))
        app.play_move(move)
        self.pump_until(lambda: len(app.board.move_stack) == 3 and not app.busy)
        app.undo()
        self.assertEqual(len(app.board.move_stack), 1)
        self.assertTrue(app.human_turn())

    def test_reset_discards_inflight_engine_result(self):
        app = self.app
        app.mode.set("Local two-player")
        app.new_game()
        app.play_move(chess.Move.from_uci("e2e4"))
        app.new_game()
        self.pump_until(lambda: app.engine_worker.jobs.empty())
        # Give a completed worker result time to reach the poller.
        for _ in range(30):
            self.root.update()
            time.sleep(0.01)
        self.assertEqual(app.board.fen(), chess.STARTING_FEN)
        self.assertEqual(app.eval_text.get(), "Evaluation  —")
        self.assertNotIn("plays e4", app.notes.get("1.0", "end"))

    def test_skip_discards_late_commentary(self):
        app = self.app
        app.mode.set("Local two-player")
        app.config = ModelConfig("lmstudio", "http://unused", "test")
        release = threading.Event()

        def slow(*args):
            release.wait(3)
            return Commentary("STALE EXPLANATION", "test")

        with patch("src.gui.gui_tk.ChessCommentator.explain", slow):
            app.play_move(chess.Move.from_uci("e2e4"))
            self.pump_until(lambda: str(app.skip_button["state"]) == "normal")
            app.skip_commentary()
            release.set()
            for _ in range(30):
                self.root.update()
                time.sleep(0.01)
        self.assertFalse(app.busy)
        self.assertNotIn("STALE", app.notes.get("1.0", "end"))

    def test_settings_do_not_persist_key(self):
        app = self.app
        app.provider.set("Remote / OpenAI-compatible")
        app.url.set("https://example.com/v1")
        app.model.set("my-model")
        app.key.set("private-test-token")
        app.apply_settings()
        text = (Path(self.temp.name) / "settings.json").read_text()
        self.assertNotIn("private-test-token", text)
        self.assertEqual(app.config.api_key, "private-test-token")

    def test_watch_pause_and_resume(self):
        app = self.app
        app.mode.set("Watch Stockfish")
        app.new_game()
        app.toggle_pause()
        for _ in range(45):
            self.root.update()
            time.sleep(0.01)
        self.assertEqual(len(app.board.move_stack), 0)
        app.toggle_pause()
        self.pump_until(lambda: len(app.board.move_stack) >= 2)
        app.toggle_pause()

    def test_terminal_position_status(self):
        app = self.app
        app.mode.set("Local two-player")
        for move in ("f3", "e5", "g4"):
            app.board.push_san(move)
        app.play_move(app.board.parse_san("Qh4#"))
        self.pump_until(lambda: not app.busy)
        self.assertIn("0-1", app.turn_text.get())
        self.assertIn("Checkmate", app.turn_text.get())

    def test_discovery_populates_picker_and_applies_selected_model(self):
        app = self.app
        app.provider.set("LM Studio")
        with patch("src.gui.settings.discover_models", return_value=["chat-a", "chat-b"]):
            app.provider_changed()
            self.pump_until(lambda: "Found 2" in app.connection.get())
        self.assertEqual(tuple(app.model_combo["values"]), ("chat-a", "chat-b"))
        app.model.set("chat-b")
        app.apply_settings()
        self.assertEqual(app.config.model, "chat-b")
        self.assertEqual(app.config.backend, "lmstudio")

    def test_edited_endpoint_discards_old_discovery(self):
        app = self.app
        app.provider.set("LM Studio")
        release = threading.Event()

        def slow(config):
            release.wait(3)
            return ["old-server-model"]

        with patch("src.gui.settings.discover_models", slow):
            app.provider_changed()
            app.url.set("http://different-server:1234/v1")
            release.set()
            for _ in range(25):
                self.root.update()
                time.sleep(0.01)
        self.assertNotIn("old-server-model", app.model_combo["values"])
