# Stockfish self-play in the browser

The demo is a static page for GitHub Pages. Opening it starts two Stockfish Web
Workers on the visitor's own device. Each visitor gets their own live game.
There is no Python server, hosted match runner, recorded playlist, model API,
owner token, or database. Closing the page ends that browser's computation.

The desktop GUI is maintained separately on the main branch.

## Test locally

Use Node.js 20+ and the included static file server:

```bash
cd pesc-i-web
npm ci --include=dev --ignore-scripts --no-audit --no-fund
npm run build:web
npm start
```

Open the URL printed by `npm start` (normally **http://127.0.0.1:8000/**).
If that port is busy, the launcher automatically tries the next available port.
To choose a different starting port, run `npm start -- --port 8080`.
Do not double-click index.html: Worker and WASM
loading need HTTP. The static file server only serves files; it does not play chess.
The browser downloads the assets and does all engine computation.

The build copies the pinned chess.js library and the Stockfish lite/single-thread
JS/WASM pair into the ignored `web/vendor/` directory. It also includes verified
corresponding source, neural-network material, and license notices for the engine.
Those build-time downloads need internet access. No external service is called
for moves while playing.

The Stockfish npm package includes larger engine variants, but only the selected
lite/single-thread pair is published. This flavor does not require cross-origin
isolation headers and works on ordinary static hosts.

## Controls and behavior

- **Pause** terminates both engine workers immediately, preserving the board.
- **Resume** starts fresh workers and continues from the existing move history.
- **New game** discards the old game and any pending engine result.
- **Flip board** changes only the view.
- **Save PGN** downloads the current game from your browser.
- Strength caps and timing settings apply with **New game**.
- The auto-next checkbox controls whether another game starts after the result.
- Hidden tabs pause automatically. Returning to the tab leaves it paused until Resume.
- The 300-ply cutoff is marked unfinished, not a draw.
- A page refresh starts a new game; browser sessions are not synchronized or persisted.

The engine uses CPU, memory, and battery on the visitor's device. Two single-threaded
workers are loaded, with only the side to move searching. Lite is smaller and
weaker than the full Stockfish build; its strength caps should not be treated as
precisely calibrated ratings.

The evaluation is from White's perspective and is labelled as the last search:
it estimates the position searched **before** the move was played, not a separate
deep analysis of the resulting position. It is approximate.

## Publish on GitHub Pages

The workflow is kept only on **main**, at `.github/workflows/pages.yml`.
It checks out **web** from the same repository and builds/tests its static assets.

1. Push both main and web to the destination repository; keep main as default.
2. In Settings → Pages → Build and deployment → Source, choose GitHub Actions.
3. In Actions, run **Deploy web branch to GitHub Pages** from main.
4. Use the URL shown by the successful deployment.

After each web update, run that workflow again. Pushes alone do not deploy.
For the complete setup and fork instructions, see
[deployment on main](https://github.com/sksubiit/pesc-i/blob/main/docs/deployment.md).

Only the built `web/` directory is uploaded. Actions builds, tests, and publishes;
it does not run an ongoing match. No personal token or model API key is needed.

## README and front page

The README preview links to the expected Pages URL. That URL becomes available
only after the workflow has deployed successfully. The preview is a static
illustration, not a live screenshot. GitHub Markdown cannot execute the game.

You can later link the same page from your profile README. To make it the root
`sksubiit.github.io` site, publish the static demo through the separate
`sksubiit.github.io` repository when you are ready.

## Turn it off

For your current session, press Pause or close the page. As the repository owner,
set `ENABLED = false` in `web/config.mjs` and redeploy to disable engine startup
for new page loads. Existing open sessions need to refresh or stop themselves.
You can also unpublish the Pages site in GitHub's settings.

## Which Stockfish?

- **Browser:** npm `stockfish@19.0.1`, Stockfish 19 Lite WASM, single-threaded.
  This is not the native executable used by Tkinter.
## Checks and source map

```bash
npm test
```

The web tests cover UCI startup ordering, timeouts, cancellation, pause/resume,
reset during search, score perspective, game endings, and automatic rematches.
An integration test runs five full games using the actual browser WASM engine
through Node's stdin/stdout transport. It does not replace browser/mobile QA.

- `web/uci.mjs`: Worker transport and UCI commands.
- `web/match.mjs`: chess rules, game lifecycle, and engine-independent controller.
- `web/app.mjs`: page rendering and controls.
- `scripts/build-web.mjs`: pinned assets, verified source/network downloads, licenses.
- `web/vendor/sources.html`: generated source/license download page.

The future goal remains Stockfish versus a recursively improving PESC-I engine.
That learning engine is not implemented here. A future browser engine could use
the same engine adapter interface; a hosted learning engine would be a separate
later architecture decision.
