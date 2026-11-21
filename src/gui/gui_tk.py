"""PESC-I desktop board. All Tk and board mutations stay on the main thread."""

from queue import Empty, Queue
import threading
import tkinter as tk
from tkinter import ttk

import chess

from src.engine.stockfish_wrapper import StockfishEngine
from src.voice.commentator import ChessCommentator, Commentary, evaluation
from src.voice.move_context import extract_move_context
from src.voice.providers import ModelConfig
from .layout import Layout, BG, MUTED
from .settings import Settings
from .workers import Worker

PIECES = dict(zip("KQRBNPkqrbnp", "♚♛♜♝♞♟♚♛♜♝♞♟"))


class ChessGUI(Layout, Settings):
    def __init__(self, root):
        self.root = root
        root.title("PESC-I · A little more insight per move")
        root.geometry("1180x850")
        root.minsize(1100, 850)
        root.configure(bg=BG)
        self.board = chess.Board()
        self.engine = StockfishEngine()
        self.results = Queue()
        self.engine_worker, self.model_worker = Worker(self.results), Worker(self.results)
        self.discovery_worker = Worker(self.results)
        self.cancelled = threading.Event()
        self.discovery_cancelled = threading.Event()
        self.comment_cancelled = threading.Event()
        self.closed = self.busy = self.paused = self.flipped = False
        self.selected = self.hint = self.last_analysis = None
        self.records = []
        self.config = ModelConfig()
        self.build_layout()
        self.load_settings()
        self.draw_board()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(40, self.poll)
        self.status.set("Your move. Click a piece to see its legal moves.")
        self.log("Stockfish does the calculating. You get the last word.", "muted")

    def poll(self):
        if self.closed:
            return
        try:
            while True:
                worker, job_id, cancelled, succeeded, value = self.results.get_nowait()
                worker.dispatch(job_id, cancelled, succeeded, value)
        except Empty:
            pass
        self.root.after(40, self.poll)

    def log(self, text, tag=""):
        self.notes.configure(state="normal")
        self.notes.insert("end", text + "\n\n", tag)
        self.notes.see("end")
        self.notes.configure(state="disabled")

    def human_turn(self):
        return self.mode.get() == "Local two-player" or (
            self.mode.get() == "Play Stockfish" and self.board.turn == (self.side.get() == "White")
        )

    def engine_turn(self):
        return not self.human_turn() and not self.board.is_game_over()

    def set_turn(self):
        outcome = self.board.outcome()
        if outcome:
            self.turn_text.set(
                f"{outcome.result()} · {outcome.termination.name.replace('_', ' ').title()}"
            )
        else:
            self.turn_text.set(
                f"{'White' if self.board.turn else 'Black'} to move"
                + (" · Check" if self.board.is_check() else "")
            )

    def square_at(self, x, y):
        file, row = int((x - 26) // 64), int((y - 26) // 64)
        if not (0 <= file < 8 and 0 <= row < 8):
            return None
        return chess.square(7 - file if self.flipped else file, row if self.flipped else 7 - row)

    def xy(self, square):
        file, rank = chess.square_file(square), chess.square_rank(square)
        return (
            26 + (7 - file if self.flipped else file) * 64,
            26 + (rank if self.flipped else 7 - rank) * 64,
        )

    def draw_board(self):
        self.canvas.delete("all")
        legal = {m.to_square for m in self.board.legal_moves if m.from_square == self.selected}
        last = self.board.peek() if self.board.move_stack else None
        for square in chess.SQUARES:
            x, y = self.xy(square)
            color = (
                "#dde4d6"
                if (chess.square_rank(square) + chess.square_file(square)) % 2
                else "#648477"
            )
            if last and square in (last.from_square, last.to_square):
                color = "#c3b76a"
            if self.hint and square in (self.hint.from_square, self.hint.to_square):
                color = "#95caaa"
            if square == self.selected:
                color = "#e4c16f"
            self.canvas.create_rectangle(x, y, x + 64, y + 64, fill=color, outline="")
            piece = self.board.piece_at(square)
            if piece:
                glyph = PIECES[piece.symbol()]
                fill, edge = ("#fff9e7", "#263b36") if piece.color else ("#172b29", "#c3d3c6")
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    self.canvas.create_text(
                        x + 32 + dx, y + 32 + dy, text=glyph, font=("DejaVu Sans", 42), fill=edge
                    )
                self.canvas.create_text(
                    x + 32, y + 32, text=glyph, font=("DejaVu Sans", 42), fill=fill
                )
            if square in legal:
                if piece:
                    self.canvas.create_rectangle(
                        x + 3, y + 3, x + 61, y + 61, outline="#a7f5cb", width=3
                    )
                else:
                    self.canvas.create_oval(
                        x + 26, y + 26, x + 38, y + 38, fill="#295d49", outline=""
                    )
        for i in range(8):
            self.canvas.create_text(
                26 + i * 64 + 32, 550, text="abcdefgh"[7 - i if self.flipped else i], fill=MUTED
            )
            self.canvas.create_text(
                12, 26 + i * 64 + 32, text=str(i + 1 if self.flipped else 8 - i), fill=MUTED
            )
        self.set_turn()

    def on_click(self, event):
        if self.busy or not self.human_turn() or self.board.is_game_over():
            return
        square = self.square_at(event.x, event.y)
        if square is None:
            return
        candidates = [
            m
            for m in self.board.legal_moves
            if m.from_square == self.selected and m.to_square == square
        ]
        if candidates:
            if len(candidates) > 1:
                self.promotion(candidates)
            else:
                self.play_move(candidates[0])
            return
        piece = self.board.piece_at(square)
        self.selected = square if piece and piece.color == self.board.turn else None
        self.draw_board()

    def promotion(self, candidates):
        dialog = tk.Toplevel(self.root)
        dialog.title("Promote your pawn")
        dialog.configure(bg=BG)
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="A small pawn. A big career change.", padding=15).pack()
        for move in candidates:
            ttk.Button(
                dialog,
                text=chess.piece_name(move.promotion).title(),
                command=lambda move=move: (dialog.destroy(), self.play_move(move)),
            ).pack(fill="x", padx=15, pady=4)
        dialog.wait_window()

    def play_move(self, move, before_analysis=None):
        if move not in self.board.legal_moves:
            return
        self.busy = True
        before = self.board.copy()
        san = before.san(move)
        self.board.push(move)
        after = self.board.copy()
        self.records.append({"san": san, "text": "", "source": ""})
        self.selected = self.hint = None
        self.refresh_history()
        self.draw_board()
        self.log(
            f"{len(self.board.move_stack)} · {'White' if before.turn else 'Black'} plays {san}",
            "heading",
        )
        self.status.set("Move played. Stockfish is checking the position…")
        self.note_status.set("ANALYZING · Engine facts arrive first")
        self.eval_text.set("Evaluation  · analyzing…")
        self.pv_text.set("Continuation  · analyzing…")
        token, limit = self.cancelled, self.limit()
        # Freeze commentary settings when the move is played.
        config, verbosity = self.config, self.verbosity.get()

        engine = self.engine

        def analyze():
            a = before_analysis or engine.analyze(before, time_limit=limit)[0]
            b = engine.analyze(after, time_limit=limit)[0]
            return a, b

        def done(pair):
            a, b = pair
            self.last_analysis = b
            self.show_analysis(b, after)
            ctx = extract_move_context(before, move, a, b, b.pv)
            self.log(ChessCommentator.engine_note(ctx), "muted")
            self.explain(ctx, token, config, verbosity)

        self.engine_worker.submit(analyze, done, self.engine_error, token)

    def show_analysis(self, analysis, board):
        self.eval_text.set("Evaluation  " + evaluation(analysis.centipawn, analysis.mate_in))
        temp, line = board.copy(), []
        for move in analysis.pv[:6]:
            if move not in temp.legal_moves:
                break
            line.append(temp.san(move))
            temp.push(move)
        self.pv_text.set("Stockfish line  " + (" ".join(line) if line else "No continuation."))

    def explain(self, ctx, game_token, config, verbosity):
        if config.backend == "template":
            self.records[-1].update(text=ChessCommentator.engine_note(ctx), source="Engine notes")
            self.note_status.set("ENGINE NOTES · Verified move facts")
            self.finish_move()
            return
        self.comment_cancelled.set()
        self.comment_cancelled = threading.Event()
        self.skip_button.configure(state="normal")
        self.status.set("Engine analysis ready. Waiting for an explanation; you can skip it.")
        self.note_status.set(f"EXPLAINING · {config.model}")

        def done(result):
            if game_token.is_set():
                return
            self.log(result.text)
            if result.error:
                self.log(f"{result.error} Showing engine notes instead.", "muted")
            self.records[-1].update(text=result.text, source=result.source)
            self.note_status.set(result.source + (" · " + result.error if result.error else ""))
            self.skip_button.configure(state="disabled")
            self.finish_move()

        def failed(exc):
            done(
                Commentary(
                    ChessCommentator.engine_note(ctx),
                    "Engine notes · fallback",
                    "The provider response could not be processed.",
                )
            )

        self.model_worker.submit(
            lambda: ChessCommentator(config, verbosity).explain(ctx),
            done,
            failed,
            self.comment_cancelled,
        )

    def finish_move(self):
        self.busy = False
        self.set_turn()
        if self.board.is_game_over():
            self.status.set("Game over. New game, new ideas.")
        elif self.paused:
            self.status.set("Paused. Resume when you're ready.")
        elif self.engine_turn():
            self.status.set("Stockfish to move…")
            token = self.cancelled
            self.root.after(350, lambda: self.advance() if not token.is_set() else None)
        else:
            self.status.set("Your move. The board is listening.")

    def skip_commentary(self):
        if str(self.skip_button["state"]) == "disabled":
            return
        self.comment_cancelled.set()
        self.skip_button.configure(state="disabled")
        self.log("Explanation skipped. Engine facts remain above.", "muted")
        self.note_status.set("ENGINE NOTES · Explanation skipped")
        self.finish_move()

    def advance(self):
        if self.busy or self.paused or not self.engine_turn() or self.closed:
            return
        self.busy = True
        snapshot, limit = self.board.copy(), self.limit()
        engine = self.engine
        self.status.set("Stockfish is thinking…")

        def done(analysis):
            self.busy = False
            if not self.paused and analysis.pv:
                self.play_move(analysis.pv[0], analysis)
            elif not self.paused:
                self.engine_error(RuntimeError("Stockfish returned no move."))

        self.engine_worker.submit(
            lambda: engine.analyze(snapshot, time_limit=limit)[0],
            done,
            self.engine_error,
            self.cancelled,
        )

    def engine_error(self, exc):
        self.busy = False
        self.paused = True
        self.pause_button.configure(text="Resume")
        self.status.set(
            "Stockfish unavailable. Check its executable path, then Resume or start again."
        )
        self.eval_text.set("Evaluation  · unavailable")
        self.pv_text.set("Set STOCKFISH_PATH to a working Stockfish executable.")
        self.note_status.set("ENGINE ERROR")
        self.log(f"Engine error: {exc}", "muted")

    def analyze_position(self):
        if self.busy or self.board.is_game_over():
            return
        self.busy = True
        self.status.set("Stockfish is looking for a hint…")
        board, limit = self.board.copy(), self.limit()
        engine = self.engine

        def done(analysis):
            self.last_analysis = analysis
            self.hint = analysis.pv[0] if analysis.pv else None
            self.show_analysis(analysis, board)
            self.draw_board()
            self.finish_move()

        self.engine_worker.submit(
            lambda: engine.analyze(board, time_limit=limit)[0],
            done,
            self.engine_error,
            self.cancelled,
        )

    def invalidate(self):
        self.cancelled.set()
        self.comment_cancelled.set()
        self.cancelled = threading.Event()
        self.comment_cancelled = threading.Event()
        self.busy = False
        self.selected = self.hint = self.last_analysis = None
        self.skip_button.configure(state="disabled")

    def refresh_history(self):
        self.history.delete(*self.history.get_children())
        board, row = chess.Board(), []
        for index, move in enumerate(self.board.move_stack):
            row.append(board.san(move))
            board.push(move)
            if index % 2 or index == len(self.board.move_stack) - 1:
                self.history.insert(
                    "", "end", values=(index // 2 + 1, row[0], row[1] if len(row) == 2 else "")
                )
                row = []
        rows = self.history.get_children()
        if rows:
            self.history.see(rows[-1])

    def new_game(self, _=None):
        self.invalidate()
        self.board.reset()
        self.records.clear()
        self.paused = False
        self.pause_button.configure(text="Pause")
        self.flipped = self.side.get() == "Black" and self.mode.get() == "Play Stockfish"
        self.refresh_history()
        self.notes.configure(state="normal")
        self.notes.delete("1.0", "end")
        self.notes.configure(state="disabled")
        self.log("Fresh board. Let's see what you find.", "muted")
        self.eval_text.set("Evaluation  —")
        self.pv_text.set("Play a move to see Stockfish's continuation.")
        self.note_status.set("READY · " + self.active_text.get())
        self.draw_board()
        self.finish_move()

    def side_changed(self, _=None):
        if self.mode.get() == "Play Stockfish":
            self.new_game()

    def undo(self):
        if not self.board.move_stack:
            return
        self.invalidate()
        self.board.pop()
        if self.records:
            self.records.pop()
        if self.mode.get() == "Play Stockfish" and not self.human_turn() and self.board.move_stack:
            self.board.pop()
            if self.records:
                self.records.pop()
        if self.mode.get() == "Watch Stockfish":
            self.paused = True
        self.pause_button.configure(text="Resume" if self.paused else "Pause")
        self.refresh_history()
        self.notes.configure(state="normal")
        self.notes.delete("1.0", "end")
        self.notes.configure(state="disabled")
        for index, record in enumerate(self.records):
            self.log(f"{index + 1} · {record['san']}", "heading")
            if record["text"]:
                self.log(record["text"])
        self.log("Move taken back. A rare luxury in chess.", "muted")
        self.eval_text.set("Evaluation  · use Hint to refresh")
        self.pv_text.set("Continuation cleared after undo.")
        self.note_status.set("READY · " + self.active_text.get())
        self.draw_board()
        self.finish_move()

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_button.configure(text="Resume" if self.paused else "Pause")
        if not self.busy:
            self.finish_move()
        elif self.paused:
            self.status.set("Pausing automatic play. Current analysis will finish.")

    def flip(self):
        self.flipped = not self.flipped
        self.draw_board()

    def on_close(self):
        self.closed = True
        self.invalidate()
        self.discovery_cancelled.set()
        # Release closures referring to Tk on its owning thread, even if HTTP is still running.
        for worker in (self.engine_worker, self.model_worker, self.discovery_worker):
            worker.close()
        threading.Thread(target=self.engine.stop, daemon=False).start()
        # Tcl timers outlive destroyed widgets unless explicitly cancelled.
        for timer in self.root.tk.call("after", "info"):
            self.root.after_cancel(timer)
        self.root.destroy()


def main():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise SystemExit(
            f"PESC-I needs a graphical display. On WSL, enable WSLg. Tk reported: {exc}"
        ) from exc
    ChessGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
