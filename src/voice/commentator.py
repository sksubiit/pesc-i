"""Engine facts first; optional language-model explanation second."""

from dataclasses import dataclass
import json

from .move_context import MoveContext
from .providers import ModelConfig, ProviderError, complete


@dataclass(frozen=True)
class Commentary:
    text: str
    source: str
    error: str = ""


def evaluation(cp, mate) -> str:
    if mate is not None:
        if mate == 0:
            return "Checkmate"
        return f"{'White' if mate > 0 else 'Black'} mates in {abs(mate)}"
    return f"{cp / 100:+.2f}" if cp is not None else "Unavailable"


class ChessCommentator:
    def __init__(self, config: ModelConfig | None = None, verbosity: str = "Brief"):
        self.config = config or ModelConfig()
        self.verbosity = verbosity

    @staticmethod
    def engine_note(ctx: MoveContext) -> str:
        if ctx.is_checkmate:
            return f"Checkmate. {ctx.side} wins. The king has run out of answers."
        target = ctx.move_uci[2:4]
        if ctx.is_castling:
            text = f"{ctx.side} castles."
        elif ctx.is_promotion:
            promoted = {"q": "queen", "r": "rook", "b": "bishop", "n": "knight"}
            text = f"{ctx.side} promotes to a {promoted[ctx.move_uci[-1]]}."
        elif ctx.piece_captured:
            text = f"{ctx.side}'s {ctx.piece_moved} captures a {ctx.piece_captured} on {target}."
        else:
            text = f"{ctx.side} moves the {ctx.piece_moved} to {target}."
        if ctx.is_check:
            text += " Check."
        if ctx.is_game_over:
            text += f" Game over: {ctx.result}."
        elif ctx.eval_delta_cp is not None:
            loss = -ctx.eval_delta_cp if ctx.side == "White" else ctx.eval_delta_cp
            if loss >= 100:
                text += f" Stockfish estimates a loss of {loss / 100:.2f} pawns versus the prior position."
        return text

    def explain(self, ctx: MoveContext) -> Commentary:
        if self.config.backend == "template":
            return Commentary(self.engine_note(ctx), "Engine notes")
        facts = {
            "move": f"{ctx.side} {ctx.move_number}. {ctx.move_san}",
            "piece": ctx.piece_moved,
            "from": ctx.move_uci[:2],
            "to": ctx.move_uci[2:4],
            "captured": ctx.piece_captured,
            "check": ctx.is_check,
            "castling": ctx.is_castling,
            "promotion": ctx.move_uci[4:] or None,
            "game_result": ctx.result,
            "evaluation_before_white_pov": evaluation(ctx.eval_before_cp, ctx.mate_before),
            "evaluation_after_white_pov": evaluation(ctx.eval_after_cp, ctx.mate_after),
            "approximate_loss_in_centipawns_for_mover": (
                max(0, -ctx.eval_delta_cp if ctx.side == "White" else ctx.eval_delta_cp)
                if ctx.eval_delta_cp is not None
                else None
            ),
            "stockfish_continuation_from_position_after_move": ctx.pv_line[:6],
            "observed_events": ctx.themes,
        }
        sentences = "1-2" if self.verbosity == "Brief" else "3-4"
        messages = [
            {
                "role": "system",
                "content": (
                    f"You explain chess moves in {sentences} clear, friendly sentences. "
                    "Use only supplied facts. Stockfish evaluates; you explain. "
                    "Scores are in pawns from White's perspective: positive favors White. "
                    "The continuation starts with the opponent's reply, not the move just played. "
                    "Do not invent threats, forks, sacrifices, intentions, or forced wins. "
                    "If the facts do not establish an idea, describe the move and evaluation honestly. "
                    "A check or capture alone does not prove a move is good. "
                    "No FEN, reasoning trace, markdown headings, or grandmaster roleplay. "
                    "A little wit is welcome; accuracy comes first."
                ),
            },
            {"role": "user", "content": json.dumps(facts)},
        ]
        try:
            text = complete(self.config, messages, 256 if self.verbosity == "Brief" else 512)
            return Commentary(text, f"{self.config.backend} / {self.config.model}")
        except ProviderError as exc:
            return Commentary(self.engine_note(ctx), "Engine notes · fallback", str(exc))
