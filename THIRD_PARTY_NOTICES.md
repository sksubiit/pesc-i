# Licensing scope and third-party notices

The root BSD-3-Clause license covers original PESC-I code and original project
assets, to the extent their contributors hold the relevant rights. It permits
commercial use and redistribution subject to its notice and disclaimer conditions.
A repository link is appreciated; it does not replace the required license notices.

It does not relicense third-party software or remove its license obligations.

## python-chess / chess

The desktop app imports python-chess, licensed under
GPL-3.0-or-later. The BSD license of original project code is GPL-compatible;
distribution of a combined application must also satisfy the applicable GPL terms.

- Source and license: https://github.com/niklasf/python-chess
- Installed chess version: 1.11.2 (python-chess metapackage: 1.999)

## Stockfish

The native desktop engine is the official Stockfish 19 Linux x86-64 universal
release, licensed under GPLv3. The verified installer keeps it locally at
`stockfish/stockfish`; the executable is not tracked or redistributed by this repo's
current tree. Its GPL license and author notices are retained alongside it.

- Official release: https://github.com/official-stockfish/Stockfish/releases/tag/sf_19
- Corresponding source: https://github.com/official-stockfish/Stockfish/tree/sf_19
- Artifact provenance and SHA-256 values: stockfish/RELEASE.json
- Native installer: scripts/install_stockfish.py

If redistributing an engine binary separately, preserve the GPL notices and provide
the corresponding source/build material required by GPLv3. The BSD license of
original PESC-I code does not relicense Stockfish.
