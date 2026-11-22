# PESC-I desktop

### Good moves. Better questions.

A desktop chess board with **Stockfish analysis** and optional **LLM explanations**.
Play against Stockfish, share a board with a friend, or watch two very stubborn
calculators negotiate. After each move, see the evaluation, a suggested continuation,
and a short explanation.

Stockfish does the chess. Your chosen language model puts words around it.
No model server or API key is required to play.

This is the **main branch: the desktop application**. The separate
[web branch](https://github.com/sksubiit/pesc-i/tree/web) contains the browser-only
Stockfish self-play demo. The desktop app does not require Node.js or a web host.

**[Watch Stockfish vs Stockfish in your browser](https://sksubiit.github.io/pesc-i/).**
The demo is hosted on GitHub Pages and deployed through GitHub Actions.
Each visitor's browser runs its own live game; Pause or close the page to stop it.
The README links to the interactive board; it cannot run the game itself.

Maintainers can publish the web branch using the deployment workflow kept on main;
see [deployment](docs/deployment.md) and [development](docs/development.md).

![PESC-I board with Stockfish analysis](docs/board.png)

## Start playing

Python 3.10+ and a graphical desktop are required. On Ubuntu / WSL:

```bash
sudo apt update
sudo apt install python3-venv python3-tk fonts-dejavu-core
git clone --depth 1 --branch main https://github.com/sksubiit/pesc-i.git
cd pesc-i
bash scripts/setup.sh
source .venv/bin/activate
pesc-i
```

Run these commands in a Linux / WSL terminal. For a fork, replace the repository
URL with your fork's URL. The shallow clone avoids downloading old binary history.
WSL needs WSLg (GUI support); SSH and headless terminals need
a graphical display. You can also launch with `python run_gui.py`.

The setup script installs the app into a project-local `.venv`. To rebuild it:

```bash
bash scripts/setup.sh --recreate
source .venv/bin/activate
pesc-i
```

`--recreate` clears this checkout's `.venv`, including packages you installed there.
It leaves the repository and your saved app preferences alone.

The setup script installs the official **Stockfish 19 Linux x86-64 universal**
executable at `stockfish/stockfish`. It verifies the release archive and executable
against pinned SHA-256 values, checks UCI startup, and replaces the engine atomically.
The native executable is local-only and ignored by Git; it is not a system install.
The first setup needs internet access for the approximately 78 MiB release download.

To install or verify the engine separately:

```bash
bash scripts/install_stockfish19.sh
```

The GUI uses `stockfish/stockfish` by default. It does not automatically choose
an engine from PATH or `/usr/games`. An explicit `STOCKFISH_PATH` still overrides
the default, for example on a platform other than Linux x86-64:

```bash
export STOCKFISH_PATH=/absolute/path/to/your/stockfish
pesc-i
```

Check the resolved engine with `python -m scripts.doctor` inside the venv.
The browser's Stockfish 19 Lite WASM is a separate web dependency and does not
replace or install the native desktop engine.

## At the board

- **Play Stockfish** — choose White or Black. Playing Black lets Stockfish open.
- **Local two-player** — both players use the same board.
- **Watch Stockfish** — engine versus engine; use Pause / Resume to control the pace.

Click a piece, then a highlighted destination. Promotions offer queen, rook,
bishop, or knight. Gold squares show the previous move; **Hint** highlights an
engine suggestion. **Flip board** changes the view.

**New game**, changing the mode, or changing your playing side starts a fresh board.
**Undo** returns to your turn against Stockfish; it takes back one move in the
other modes. Undo pauses a watched game.

The right panel shows:

- Whose turn it is, check, and the final result.
- Stockfish's evaluation in pawns: **positive favors White**, negative favors Black.
  Mate scores name the winning side.
- A legal continuation from the position **after** the move.
- Engine notes, followed by the selected model's explanation.

Analysis and network requests run in the background. A slow model doesn't stop
you using the controls: **Continue without explanation** skips that move's prose.
Skipped or reset results are discarded; an already-sent request may still finish
on the server. Automatic play waits for each explanation so it doesn't flood a
local model with requests.

## Choose a commentator

Open **Commentary setup**, choose a provider, select a discovered model (or type its
exact ID), and click **Apply commentary settings**. Settings apply to the next move.
The active provider is displayed separately from the settings being edited.

| Provider                   | Base URL                                            | Model discovery                       |
| -------------------------- | --------------------------------------------------- | ------------------------------------- |
| Engine notes (offline)     | None                                                | None needed                           |
| LM Studio                  | `http://localhost:1234/v1`                        | `GET /v1/models`                    |
| Ollama                     | `http://localhost:11434`                          | `GET /api/tags`                     |
| Remote / OpenAI-compatible | Your provider's API base, usually ending in `/v1` | `GET /models` relative to that base |

Local providers are checked when selected. **Find available models** refreshes the
list after loading or downloading another model. Discovery lists what the server
reports; it doesn't benchmark quality or guarantee that every listed model supports
chat. Embedding models are filtered out by name.

### LM Studio

1. Install [LM Studio](https://lmstudio.ai/), download a chat/instruct model, and load it.
2. Start the local server in LM Studio's Developer area.
3. Select **LM Studio** in PESC-I. Check the URL, find models, choose one, and Apply.
4. If you enabled server authentication, enter its token in the API key field.

PESC-I uses LM Studio's documented [model listing](https://lmstudio.ai/docs/developer/openai-compat/models)
and [OpenAI-compatible chat endpoint](https://lmstudio.ai/docs/developer/openai-compat).
The listed models may include downloaded models available for just-in-time loading.

### Ollama

Install [Ollama](https://ollama.com/), then download a chat model you want to use:

```bash
ollama pull <model-name>
ollama list
ollama serve
```

Replace `<model-name>` with an actual model ID. If Ollama is already running,
you don't need another `ollama serve` process.

Select **Ollama**, find models, choose a downloaded model, and Apply.
The app uses Ollama's native [model list](https://docs.ollama.com/api/tags)
and [chat API](https://docs.ollama.com/api/chat); leave `/v1` off the Ollama base URL.

### Remote APIs

Choose **Remote / OpenAI-compatible**, enter the provider's base URL and API key,
and find models. If the service doesn't expose a model list, type the model ID
from its documentation and Apply.

The service must support **Chat Completions** with `model`, `messages`,
`max_tokens`, and `temperature`. APIs that require another protocol or different
parameters need an adapter; selecting a provider doesn't make all APIs compatible.

Use the following base URLs with **Remote / OpenAI-compatible**. Enter the API
key issued by that provider and choose a model available to your account.
Do not append `/chat/completions`; the app adds that path automatically.

| Provider | Base URL | Compatibility notes |
| --- | --- | --- |
| OpenAI | `https://api.openai.com/v1` | Default remote URL; choose a model that accepts the request parameters above. |
| Google Gemini / AI Studio | `https://generativelanguage.googleapis.com/v1beta/openai/` | Use a Gemini API key and Google's OpenAI-compatible endpoint. |
| Groq | `https://api.groq.com/openai/v1` | Use a Groq API key and a supported chat model. |
| Mistral | `https://api.mistral.ai/openai/v1` | Dedicated OpenAI-compatible endpoint; currently documented as public preview. |
| Anthropic / Claude | `https://api.anthropic.com/v1/` | Conditional compatibility; see below. |

See the provider documentation for [Google Gemini](https://aistudio.google.com/docs/openai),
[Groq](https://console.groq.com/docs/openai),
[Mistral](https://docs.mistral.ai/inference/conversations/chat-completion), and
[Anthropic](https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk).
These are configuration references, not a claim that every provider/model has
been tested with PESC-I.

The current remote client uses raw HTTP with bearer authentication, rather than
a provider-specific SDK. Anthropic documents its compatibility layer for official
OpenAI SDKs; some Anthropic keys also require an `anthropic-workspace-id` header,
which this GUI does not currently support. A base URL alone is therefore not a
guarantee that Claude requests will work.

Model discovery can fail independently of chat generation. If **Find available
models** fails, you can still enter an exact model ID manually. Model-specific
parameters and response formats may require changes to the client.

Keep **Ollama** selected for Ollama's native API and **LM Studio** for its local
server. Use the remote option for the cloud providers above.

You can supply the remote key through the masked field or `PESC_I_API_KEY` in the
launching shell. Keys are kept in memory and are never written to preferences.
Move facts and Stockfish scores are sent to the selected endpoint. Remote calls
may incur the provider's normal charges. There is no automatic switch to a paid API.

### Local server on Windows, board in WSL

Try `localhost` first. If the Windows server is unreachable from WSL, use the
Windows host address as seen from your WSL network. In the usual NAT configuration,
`ip route show default` shows the gateway address; mirrored networking behaves
differently. Do not assume the DNS nameserver is the Windows host.

Change the URL in the app, for example `http://<windows-host>:1234/v1` or
`http://<windows-host>:11434`. Configure the server to listen on a reachable
interface and allow the connection through Windows Firewall on your private network.
For Ollama, see its [network configuration guide](https://docs.ollama.com/faq).
Only expose your model server to networks you trust.

## About explanation quality

**The current prompts are basic, somewhat vague, and experimental. Do not expect
expert chess analysis from the LLM commentary.** Quality depends on the prompt,
the supplied context, and the model—not just model size or whether it runs locally.

Brief and Detailed currently use the same move facts and almost the same prompt:

| Mode | Requested response | Maximum generated tokens |
| --- | --- | ---: |
| Brief | 1–2 clear, friendly sentences | 256 |
| Detailed | 3–4 clear, friendly sentences | 512 |

Detailed does not currently request a separate, deeper analysis. Both modes
receive move facts, evaluations before/after, and a short Stockfish continuation;
they do not receive the full board position, game history, or the best alternative
before the move. A model may produce similar or identical text in both modes, and
the requested sentence count is not enforced.

Increasing the request timeout only gives the server longer to respond. It does
not increase the token limit or ask for better analysis. Length settings are
captured when a move is played and apply to that move's new explanation.

The prompt is built in [commentator.py](src/voice/commentator.py), while
[providers.py](src/voice/providers.py) sends the request and handles the response.
Stockfish's numerical evaluation and legal continuation are separate from the
model's interpretation.

A language model can sound confident while being wrong. Smaller models are
particularly fond of finding imaginary forks. PESC-I supplies concrete move facts,
White-perspective scores, and a legal Stockfish continuation, with instructions
to avoid unsupported tactical claims. This improves grounding; it does **not**
turn a language model into a chess engine.

Use a chat/instruct model that runs comfortably on your hardware. Try Brief first.
The offline notes are always available and make fewer promises.
Cold model loading can take longer than the request timeout. Reasoning models may
also spend their token budget thinking and return no usable explanation; try a
chat/instruct model instead. Ollama requests disable optional thinking for these
short explanations. Failed requests,
authentication errors, timeouts, and empty replies visibly fall back to engine
notes. The board's evaluation always comes from Stockfish.

Evaluations and move-loss estimates depend on the search budget; they are not
certified move grades. Increase the engine time for a steadier analysis.
“Voice” currently means written commentary, not synthesized audio.

## Desktop and web side by side

Git worktrees let you keep both branches open in separate folders while sharing
one repository's history and remotes:

```text
pesc-i/       main — desktop app, .venv, native Stockfish
pesc-i-web/   web  — browser app, node_modules, generated browser assets
```

From a desktop checkout, create the web worktree once:

```bash
cd pesc-i
git fetch origin web:refs/remotes/origin/web
git worktree add --track -b web ../pesc-i-web origin/web
git worktree list
```

These commands also work after the shallow clone above. They assume the web branch
exists on the remote named `origin`; replace `origin` if you use another remote
name, such as `upstream`. If a local `web` branch already exists, use
`git worktree add ../pesc-i-web web` instead of the `--track -b` command.
If both folders already appear in `git worktree list`, use them directly.

Run the desktop from `pesc-i/` using its venv. In another terminal, run the browser
edition with Node.js 20+:

```bash
cd pesc-i-web
npm ci --include=dev --ignore-scripts --no-audit --no-fund
npm run build:web
npm start
```

Open the URL printed by the launcher. Run dependency installation and the build
on first setup and after relevant dependency or build changes; `npm start` serves
the built files locally.

Each folder has its own working files and staging area. Commit desktop changes
from `pesc-i/` on main and browser changes from `pesc-i-web/` on web.
Keep these product branches separate rather than merging them wholesale.
The deployment workflow stays on main and publishes the web branch.
See [development](docs/development.md) and [deployment](docs/deployment.md) for details.

## Troubleshooting and development

```bash
source .venv/bin/activate
python -m scripts.doctor
bash scripts/check.sh
# Optional linting
python -m pip install -e '.[dev]'
ruff check src tests scripts run_gui.py
```

Tests exercise real Stockfish analysis, local mock HTTP servers, and the Tk workflow.
GUI tests skip on a headless machine; run under WSLg or `xvfb-run` to include them.
Tests never call a paid model API.

- **No window:** check WSLg / DISPLAY and that `python3-tk` is installed.
- **Engine error:** check `STOCKFISH_PATH`, executable permissions, and architecture.
- **No models:** start the server, load/pull a chat model, then refresh.
- **Remote authentication or model error:** check the key, API base URL, and exact model ID.
- **Long explanations:** shorten the response, adjust the timeout, or skip the prose.

Preferences live at `~/.config/pesc-i/settings.json` (or under `XDG_CONFIG_HOME`).
They restore as a draft; click Apply to enable the provider each session.
Delete that file to reset preferences.

Code is split into `src/engine` (Stockfish), `src/voice` (facts and provider clients),
and `src/gui` (desktop layout and game flow). `run_gui.py` is a convenience launcher.
The old `src/gui_tk.py` import remains a compatibility shim.

The locally installed Stockfish is GPLv3 software. Its official license and author
notices are retained in `stockfish/COPYING.txt` and `stockfish/AUTHORS`.
[Release provenance](stockfish/RELEASE.json) records the verified sf_19 artifact,
checksums, and [corresponding upstream source](https://github.com/official-stockfish/Stockfish/tree/sf_19).
Native executables and backups are excluded from Git.

## License

Original PESC-I code and assets use [BSD-3-Clause](LICENSE), allowing
commercial use subject to its license-notice conditions. A repository credit is
appreciated; it does not replace preserving the required notices.
[Third-party notices](THIRD_PARTY_NOTICES.md) describe Stockfish and python-chess,
which retain their GPL licenses.

The desktop API key field is session-only. Apply does not save the key to disk.
For the remote provider, `PESC_I_API_KEY` may be supplied by the launching process.
The app does not automatically load `.env` files. Keep persistent secrets outside
the repository, for example in an OS credential store or private launcher.
