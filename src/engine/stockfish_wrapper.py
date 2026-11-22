"""Stockfish engine wrapper with a clean API for analysis and play."""

import chess
import chess.engine
import os
import threading
from dataclasses import dataclass
from typing import Optional, List


def stockfish_path() -> str:
    """Use an explicit override or this checkout's sole native engine."""
    return os.environ.get("STOCKFISH_PATH") or os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "stockfish", "stockfish")
    )


STOCKFISH_PATH = stockfish_path()


@dataclass
class MoveResult:
    """Result from an engine play request."""

    move: chess.Move
    ponder: Optional[chess.Move] = None


@dataclass
class Analysis:
    """Result from an engine analysis request."""

    score: chess.engine.PovScore
    pv: List[chess.Move]
    depth: int

    @property
    def centipawn(self) -> Optional[int]:
        """Centipawn score from White's perspective, or None if mate."""
        return self.score.white().score()

    @property
    def mate_in(self) -> Optional[int]:
        """Mate-in-N from White's perspective, or None."""
        return self.score.white().mate()


class StockfishEngine:
    """Clean wrapper around Stockfish via python-chess.

    Thread-safe: guards the underlying engine process with a lock.
    """

    def __init__(self, path: str = STOCKFISH_PATH):
        self.path = path
        self._engine: Optional[chess.engine.SimpleEngine] = None
        self._lock = threading.Lock()

    # -- lifecycle --------------------------------------------------------

    def start(self) -> None:
        """Start the engine process (idempotent)."""
        with self._lock:
            if self._engine is None:
                if not os.path.isfile(self.path):
                    raise FileNotFoundError(
                        "Stockfish is missing. Run bash scripts/install_stockfish19.sh "
                        "or set STOCKFISH_PATH to an explicit executable."
                    )
                self._engine = chess.engine.SimpleEngine.popen_uci(self.path)

    def stop(self) -> None:
        """Stop the engine process (idempotent)."""
        with self._lock:
            if self._engine is not None:
                try:
                    self._engine.quit()
                except Exception:
                    pass
                self._engine = None

    @property
    def is_running(self) -> bool:
        return self._engine is not None

    @property
    def name(self) -> str:
        self.start()
        with self._lock:
            return self._engine.id.get("name", "Unknown engine")

    # -- configuration ----------------------------------------------------

    def set_elo(self, elo: int) -> None:
        """Limit engine strength to a supported UCI Elo value."""
        self.start()
        with self._lock:
            self._engine.configure({"UCI_LimitStrength": True, "UCI_Elo": elo})

    def set_full_strength(self) -> None:
        self.start()
        with self._lock:
            self._engine.configure({"UCI_LimitStrength": False})

    # -- play & analysis --------------------------------------------------

    def get_best_move(
        self,
        board: chess.Board,
        time_limit: Optional[float] = None,
        depth: Optional[int] = None,
    ) -> MoveResult:
        """Return the engine's best move for *board*."""
        self.start()
        limit = self._make_limit(time_limit, depth)
        with self._lock:
            result = self._engine.play(board, limit)
        return MoveResult(move=result.move, ponder=result.ponder)

    def analyze(
        self,
        board: chess.Board,
        time_limit: Optional[float] = None,
        depth: Optional[int] = None,
        multipv: int = 1,
    ) -> List[Analysis]:
        """Analyse the position and return one or more principal variations."""
        self.start()
        limit = self._make_limit(time_limit, depth)
        with self._lock:
            infos = self._engine.analyse(board, limit, multipv=multipv)
        if isinstance(infos, dict):
            infos = [infos]
        return [
            Analysis(
                score=info.get(
                    "score",
                    chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE),
                ),
                pv=info.get("pv", []),
                depth=info.get("depth", 0),
            )
            for info in infos
        ]

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _make_limit(
        time_limit: Optional[float],
        depth: Optional[int],
    ) -> chess.engine.Limit:
        if depth and depth > 0:
            return chess.engine.Limit(depth=depth)
        if time_limit and time_limit > 0:
            return chess.engine.Limit(time=time_limit)
        return chess.engine.Limit(time=0.2)
