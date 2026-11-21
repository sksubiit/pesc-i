import unittest
import chess

from src.engine.stockfish_wrapper import StockfishEngine
from src.voice.move_context import extract_move_context
from src.voice.commentator import ChessCommentator


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = StockfishEngine()

    @classmethod
    def tearDownClass(cls):
        cls.engine.stop()

    def test_real_analysis_and_legal_continuation(self):
        board = chess.Board()
        before = self.engine.analyze(board, depth=7)[0]
        move = chess.Move.from_uci("e2e4")
        after_board = board.copy()
        after_board.push(move)
        after = self.engine.analyze(after_board, depth=7)[0]
        context = extract_move_context(board, move, before, after, after.pv)
        self.assertEqual(context.move_san, "e4")
        self.assertEqual(context.pv_line[0], after_board.san(after.pv[0]))
        self.assertEqual(context.eval_delta_cp, after.centipawn - before.centipawn)
        self.assertEqual(board.fen(), chess.STARTING_FEN)
        self.assertTrue(self.engine.get_best_move(board, depth=5).move in board.legal_moves)

    def test_multipv(self):
        analyses = self.engine.analyze(chess.Board(), depth=5, multipv=2)
        self.assertEqual(len(analyses), 2)

    def test_checkmate(self):
        board = chess.Board()
        for san in ("f3", "e5", "g4"):
            board.push_san(san)
        move = board.parse_san("Qh4#")
        context = extract_move_context(board, move)
        self.assertTrue(context.is_checkmate)
        self.assertEqual(context.result, "0-1")
        self.assertIn("Black wins", ChessCommentator.engine_note(context))

    def test_underpromotion_and_capture_facts(self):
        board = chess.Board("7k/P7/8/8/8/8/8/7K w - - 0 1")
        context = extract_move_context(board, chess.Move.from_uci("a7a8n"))
        self.assertIn("knight", ChessCommentator.engine_note(context))
        board = chess.Board("7k/8/8/8/8/8/p7/R6K w - - 0 1")
        context = extract_move_context(board, chess.Move.from_uci("a1a2"))
        self.assertNotIn("sacrifice", context.themes)
