# Licensing scope and third-party notices

The root BSD-3-Clause license covers original PESC-I code and original project
assets, to the extent their contributors hold the relevant rights. It permits
commercial use and redistribution subject to its notice and disclaimer conditions.
A repository link is appreciated; it does not replace the required license notices.

It does not relicense third-party software or remove its license obligations.

## python-chess / chess

The desktop app and broadcast generator import python-chess, licensed under
GPL-3.0-or-later. The BSD license of original project code is GPL-compatible;
distribution of a combined application must also satisfy the applicable GPL terms.

- Source and license: https://github.com/niklasf/python-chess
- Installed chess version: 1.11.2 (python-chess metapackage: 1.999)

## Stockfish

Stockfish is a separate UCI engine under GPLv3. The existing bundled Linux binary
identifies itself as Stockfish 17.1. Its license is in stockfish/COPYING.txt.

- Upstream: https://github.com/official-stockfish/Stockfish
- Version source: https://github.com/official-stockfish/Stockfish/tree/sf_17.1

A version tag alone does not establish that it is the exact corresponding source
for an arbitrary prebuilt binary. Before redistributing the bundled binary, verify
its provenance and supply the corresponding source/build material required by GPLv3,
or obtain Stockfish separately through the operating-system package manager.
PESC-I's BSD license does not apply to the Stockfish binary.

