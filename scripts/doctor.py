"""Report local prerequisites; never contact a model provider."""

import os
import platform
import sys
import tkinter

from src.engine.stockfish_wrapper import StockfishEngine

print("Python:", sys.version.split()[0], platform.system(), platform.machine())
print("Display:", os.environ.get("DISPLAY", "(unset)"))
engine = StockfishEngine()
print("Stockfish:", engine.path)
try:
    import chess

    result = engine.get_best_move(chess.Board(), time_limit=0.1)
    print("Engine version:", engine.name)
    print("Engine ready:", result.move.uci())
finally:
    engine.stop()
try:
    root = tkinter.Tk()
    root.withdraw()
    root.destroy()
    print("Tk display: ready")
except tkinter.TclError as exc:
    print("Tk display unavailable:", exc)
    sys.exit(1)
