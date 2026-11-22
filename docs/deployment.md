# Publishing the browser demo

The repository has two product branches:

- **main** contains the desktop app and the deployment workflow.
- **web** contains the browser demo, its build scripts, tests, and npm lockfile.

The workflow lives at `.github/workflows/pages.yml` on main. It explicitly checks
out **web from the same repository**, builds and tests that revision, and publishes
only its generated `web/` folder. No browser source or npm dependencies are needed
in the main checkout.

## Initial setup for a repository or fork

1. Push both branches to the destination repository. It must contain a branch
   named `web`, and its default branch must be `main`. Forks that copied only the
   default branch need to add/push the web branch too.
2. Enable GitHub Actions if the repository or fork has it disabled.
3. In **Settings → Pages → Build and deployment → Source**, choose **GitHub Actions**.
4. If the `github-pages` environment restricts deployment branches, allow **main**.
   The workflow runs on main even though its build checks out web.
5. Open **Actions → Deploy web branch to GitHub Pages → Run workflow**.
   Select **main**, then run it.

For an ordinary project repository, the resulting address is
`https://OWNER.github.io/REPOSITORY/`, using the destination repository's owner and
name. The project's canonical address is https://sksubiit.github.io/pesc-i/.
Relative asset URLs allow forks to use their own project path.

## Publishing an update

Commit and push browser changes to `web`. Then run the workflow on `main`.

A web push alone does not trigger deployment: the workflow deliberately exists
only on main. This keeps deployment explicit without a second workflow, scheduled
polling, or a custom dispatch token.

Each run records the exact checked-out web commit in the Actions summary. Only
after build and tests succeed can the deploy job publish its artifact. New runs
cancel older deployment runs. Upload artifacts are retained for one day.

To update deployment behavior, edit the workflow on main. To update page behavior,
edit source/build scripts on web. Do not merge the two product branches wholesale.

## Credentials, usage, and visibility

No model key, personal access token, or hosting-machine credential is required.
GitHub supplies its normal workflow token. The build job has read access; the
separate deploy job has Pages and deployment-identity permissions. Checkout
credentials are not persisted into browser build scripts.

Standard GitHub-hosted runner compute for public repositories is currently free
and does not reduce included compute usage. Private repositories draw from the
owner's plan. Artifact/storage and service limits still apply. See
[Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
and [Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).

Actions runs briefly to install dependencies, build, and test (including a few
self-play games), then publishes static files. Visitors' browsers perform their
own game computation; visits do not trigger Actions runs or a hosted game server.

The README can show a static preview and link to the page. It cannot execute the
interactive game.

## Disable the demo

In the web branch, set `ENABLED = false` in `web/config.mjs`, push it, then deploy
from main. That stops engine startup for refreshed/new sessions. Existing open
sessions need to stop or refresh themselves. To stop serving the website entirely,
use the repository's Pages unpublish setting.
