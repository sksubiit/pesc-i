"""Extract structured context from a chess move for LLM commentary."""

from __future__ import annotations

import chess
from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.engine.stockfish_wrapper import Analysis


PIECE_NAMES = {
    chess.PAWN: "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK: "rook",
    chess.QUEEN: "queen",
    chess.KING: "king",
}


@dataclass
class MoveContext:
    """Everything an LLM needs to commentate on a single move."""

    # Position
    fen_before: str
    fen_after: str
    move_san: str
    move_uci: str
    move_number: int
    side: str  # "White" or "Black"

    # Evaluation (centipawns, White's perspective)
    eval_before_cp: Optional[int] = None
    eval_after_cp: Optional[int] = None
    eval_delta_cp: Optional[int] = None
    mate_before: Optional[int] = None
    mate_after: Optional[int] = None

    # Principal variation (SAN strings)
    pv_line: List[str] = field(default_factory=list)

    # Move properties
    is_capture: bool = False
    is_check: bool = False
    is_checkmate: bool = False
    is_castling: bool = False
    is_en_passant: bool = False
    is_promotion: bool = False
    piece_moved: str = ""
    piece_captured: Optional[str] = None

    # Game state after the move
    is_game_over: bool = False
    result: Optional[str] = None  # "1-0", "0-1", "1/2-1/2"

    # Tactical / positional themes (detected heuristically)
    themes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_move_context(
    board_before: chess.Board,
    move: chess.Move,
    eval_before: Optional["Analysis"] = None,
    eval_after: Optional["Analysis"] = None,
    pv: Optional[List[chess.Move]] = None,
) -> MoveContext:
    """Build a *MoveContext* for *move* about to be played on *board_before*."""

    move_san = board_before.san(move)
    board_after = board_before.copy()
    board_after.push(move)

    # Piece info
    piece = board_before.piece_at(move.from_square)
    captured = board_before.piece_at(move.to_square)
    # en-passant captures have no piece on to_square
    if board_before.is_en_passant(move) and captured is None:
        captured_type_name = "pawn"
    else:
        captured_type_name = PIECE_NAMES.get(captured.piece_type) if captured else None

    # Eval
    eb_cp = eval_before.centipawn if eval_before else None
    ea_cp = eval_after.centipawn if eval_after else None
    mate_b = eval_before.mate_in if eval_before else None
    mate_a = eval_after.mate_in if eval_after else None
    delta = (ea_cp - eb_cp) if (eb_cp is not None and ea_cp is not None) else None

    # PV as SAN
    pv_san: List[str] = []
    if pv:
        temp = board_after.copy()
        for pv_move in pv:
            if pv_move in temp.legal_moves:
                pv_san.append(temp.san(pv_move))
                temp.push(pv_move)
            else:
                break

    # Game result
    result = None
    if board_after.is_game_over():
        outcome = board_after.outcome()
        if outcome:
            result = outcome.result()

    # Themes
    themes = _detect_themes(board_before, board_after, move, delta)

    return MoveContext(
        fen_before=board_before.fen(),
        fen_after=board_after.fen(),
        move_san=move_san,
        move_uci=move.uci(),
        move_number=board_before.fullmove_number,
        side="White" if board_before.turn == chess.WHITE else "Black",
        eval_before_cp=eb_cp,
        eval_after_cp=ea_cp,
        eval_delta_cp=delta,
        mate_before=mate_b,
        mate_after=mate_a,
        pv_line=pv_san,
        is_capture=board_before.is_capture(move),
        is_check=board_after.is_check(),
        is_checkmate=board_after.is_checkmate(),
        is_castling=board_before.is_castling(move),
        is_en_passant=board_before.is_en_passant(move),
        is_promotion=move.promotion is not None,
        piece_moved=PIECE_NAMES.get(piece.piece_type, "piece") if piece else "piece",
        piece_captured=captured_type_name,
        is_game_over=board_after.is_game_over(),
        result=result,
        themes=themes,
    )


# ---------------------------------------------------------------------------
# Theme detection (heuristic)
# ---------------------------------------------------------------------------

CENTER_SQUARES = {chess.E4, chess.D4, chess.E5, chess.D5}


def _detect_themes(
    board_before: chess.Board,
    board_after: chess.Board,
    move: chess.Move,
    delta: Optional[int],
) -> List[str]:
    themes: List[str] = []

    # Eval-based themes
    if delta is not None:
        is_white = board_before.turn == chess.WHITE
        # A positive delta favours White; normalise so "good for the side to move"
        swing = delta if is_white else -delta
        if abs(delta) > 200:
            themes.append("critical moment")
        if swing > 100:
            themes.append("strong move")
        elif swing < -100:
            themes.append("inaccuracy")
        if swing < -300:
            # override "inaccuracy" with the stronger label
            themes = [t for t in themes if t != "inaccuracy"]
            themes.append("blunder")

    # Tactical motifs
    if board_after.is_checkmate():
        themes.append("checkmate")
    elif board_after.is_check():
        themes.append("check")

    if board_before.is_capture(move):
        themes.append("capture")

    if board_before.is_castling(move):
        themes.append("castling")
    if move.promotion:
        themes.append("promotion")
    if board_before.is_en_passant(move):
        themes.append("en passant")
    if move.to_square in CENTER_SQUARES:
        themes.append("move to a central square")
    if board_after.is_stalemate():
        themes.append("stalemate")

    return themes
