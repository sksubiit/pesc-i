# Third-party notices — browser edition

The [BSD-3-Clause license](LICENSE) covers original PESC-I code and assets.
It permits commercial use subject to its notice and disclaimer conditions.
It does not relicense third-party software.

## Stockfish.js / Stockfish

The browser build uses `stockfish@19.0.1`, Stockfish 19 Lite single-threaded WASM,
under GPLv3. The build publishes the selected engine, license, corresponding
source archive, and neural-network material alongside the page. Preserve those
materials and required notices when redistributing the generated website.

- Package: https://www.npmjs.com/package/stockfish/v/19.0.1
- Source: https://github.com/nmrugg/stockfish.js/tree/0d5dd7944f88c817c07a26bc4fb1905d5f9c46d6
- Upstream: https://github.com/official-stockfish/Stockfish
- Build/provenance checks: `scripts/build-web.mjs`
- Generated downloadable material: `web/vendor/sources.html`
- Generated artifact checksums: `web/vendor/manifest.json`

The npm package includes other engine variants. Only the Lite single-threaded
pair is published by this build. This branch does not ship a native desktop engine.

## chess.js

Chess rules use chess.js 1.4.0, licensed under BSD-2-Clause.

- Source: https://github.com/jhlywa/chess.js/tree/v1.4.0

The build copies its license into the generated vendor directory. Keep that
notice with redistributed builds. See the generated source/license page for
the exact download links.
