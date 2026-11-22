# Repository development

## Product branches

| Branch | Responsibility |
| --- | --- |
| main | Desktop Python/Tk app, native engine installer, desktop/provider tests, deployment control |
| web | Browser self-play UI, Worker/UCI adapter, static asset builder, browser tests |

These are long-lived product branches, not feature branches that should be merged
back into each other. Keep feature branches based on the product being changed.
Apply truly shared fixes (such as license text) selectively rather than merging
all desktop files into web or web files into main.

Original PESC-I code is BSD-3-Clause. Third-party licenses remain applicable;
each product branch has its own relevant THIRD_PARTY_NOTICES.md.

## Desktop files on main

- `src/gui/`: widgets, board interaction, and desktop game flow.
- `src/engine/`: project-local native Stockfish wrapper.
- `src/voice/`: move context, optional model providers, and commentary.
- `scripts/setup.sh`: venv creation and verified native engine installation.
- `scripts/install_stockfish.py`: pinned official release, checksum and UCI checks.
- `scripts/doctor.py`: display/engine diagnostics.
- `tests/`: desktop, provider, and installer regressions.
- `stockfish/`: notices/provenance plus the locally installed, ignored executable.

Run desktop checks after setup:

```bash
source .venv/bin/activate
bash scripts/check.sh
python -m scripts.doctor
```

Optional linting:

```bash
python -m pip install -e '.[dev]'
ruff check src tests scripts run_gui.py
```

GUI tests need a display such as WSLg/X11 and otherwise skip. Provider tests use
local mock HTTP servers, not paid API calls.

## Parallel local development

Use separate checkouts or Git worktrees so desktop and browser dependencies do
not get mixed. From an existing desktop checkout:

```bash
git fetch origin
git worktree add ../pesc-i-web web
```

If web exists only on the remote:

```bash
git worktree add --track -b web ../pesc-i-web origin/web
```

Replace `origin` with the remote name used for your fork if necessary. The web
README contains its own build/test instructions. Keep `.venv/` and the native
engine in the desktop checkout; keep `node_modules/` and generated vendor files
in the web checkout. These are local artifacts, not files to commit.

## Publishing

Commit desktop changes on main and browser changes on web. Push both branches to
the same destination repository. Deployment is then requested from the workflow
on main; see [deployment.md](deployment.md).

Keep secrets in the local environment or private credential storage. Never add
model API keys or runtime caches to commits. Do not commit native executables,
node_modules, or generated web vendor assets.
