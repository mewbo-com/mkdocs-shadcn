# CLAUDE.md

Scoped working notes for this repository. Self-contained: everything here is
about navigating and changing *this* repo, not anything that consumes it.

## What this is

A packaged MkDocs **theme + plugins** (`shadcn` theme entrypoint) — a brand
fork that layers Mewbo customizations on top of an upstream theme and is
periodically re-synced from an `upstream` git remote (see "Syncing upstream").
The wheel ships the `shadcn/` package only.

## Build & dev commands

- **CSS:** `bun run build` compiles `tailwind/main.css` → `shadcn/css/base.css`
  (minified). `base.css` is a **committed build artifact** — `mkdocs build`
  does NOT run Tailwind, so after editing anything under `tailwind/` you must
  rebuild and commit `base.css`. A pre-commit hook (`build-css`) does this
  automatically when `tailwind/*.css` changes; `bun install` is required first
  (no committed JS lockfile — JS lockfiles are gitignored).
- **Python env / tests:** `uv sync --all-extras --dev`, then
  `uv run playwright install chromium` (and `firefox`/`webkit` for full CI
  parity; webkit needs system libs via `playwright install-deps`).
- **Dev CLI:** `uv run python manage.py <command>` (Typer app in `internal/`),
  e.g. `manage.py integrity`, `manage.py serve`, `manage.py test`.
- **Lint:** `uv run ruff check .` and `uv run ruff format .` (target py38,
  line-length 79). `pre-commit` also runs ruff + a `sync-version` hook.

## Layout

- `tailwind/*.css` — CSS source, compiled into `shadcn/css/base.css`.
- `shadcn/css/mewbo.css` — Mewbo brand overrides, hand-written, linked **after**
  `base.css` in `main.html` so it wins the cascade and survives CSS recompiles.
- `shadcn/main.html` — base template. `shadcn/templates/*.html` — partials;
  `shadcn/templates/external/*.html` — optional integrations (katex, echarts,
  pygments, mkdocstrings, codexec).
- `shadcn/plugins/` — a custom `SearchPlugin` subclass composed from
  `plugins/mixins/*` (i18n, git, dev, order, mkdocstrings, katex, table,
  markdown). The `TableMixin` wraps every `<table>` in
  `<div class="table-wrapper">` via `on_page_content`.
- `shadcn/js/*.js` — theme + Mewbo enhancement scripts.
- `pages/` — the demo/docs site (`pages/mkdocs.yml`); `tests/` — Playwright.
- `internal/` + `manage.py` — dev tooling (not shipped in the wheel).

## Conventions & gotchas (learned the hard way)

- **Tables word-wrap by default.** `tailwind/table.css` deliberately does NOT
  put `whitespace-nowrap` on `th`/`td` (it uses `break-words`); the
  `.table-wrapper` keeps `overflow-x:auto` only as a fallback for un-wrappable
  content. Do not reintroduce `nowrap` — `tests/test_browser.py::`
  `test_tables_wrap_no_horizontal_scroll` (fixture: `pages/docs/`
  `table_wrap_regression.md`) fails if cells compute to `white-space:nowrap` or
  a table overflows horizontally. Use `class="nowrap"` to opt a cell out.
- **Template includes use the `templates/` prefix.** The Jinja loader root is
  `shadcn/`, so write `{% include "templates/icon.html" %}` /
  `{% from "templates/_nav_icon_map.html" import nav_icon %}`. There is no
  `components/` directory.
- **Never rebind `_` in a template.** `_` is gettext (i18n). The throwaway
  idiom `{% set _ = somelist.append(x) %}` rebinds `_` to `None` and breaks
  every `{{ _("...") }}` that follows with `'NoneType' object is not callable`.
  Use `{% set _unused = ... %}` (or `{% do %}`).
- **SRI integrity is baked into templates.** `manage.py integrity` hashes each
  local `<script src='js/*.js'>` and writes an `integrity="sha384-…"` attr.
  After editing any `shadcn/js/*.js`, re-run `manage.py integrity --force` or
  the changed script will be blocked by the browser (SRI mismatch → console
  error → the Playwright crawler test fails). The tool uses BeautifulSoup and
  reserializes the touched template, so keep void tags self-closed (e.g.
  `<link ... />`) to avoid stray `</link>` artifacts.
- **Versioning.** This fork uses its own SemVer (`1.x`) independent of
  upstream's `0.10.x`. `pyproject.toml` is the source of truth; the
  `sync-version` hook copies it into `package.json`.

## Testing

`uv run pytest` builds the `pages/` site once per session into `tests/_site`
and serves it (default `127.0.0.1:8081`; override with `MKDOCS_TEST_PORT`).
`tests/_site` is cached — **`rm -rf tests/_site` after changing CSS/templates**
so the rebuild picks up your changes. `test_all_pages_no_browser_errors` crawls
every page and fails on any console/page error (this is what catches broken
templates, bad includes, and SRI mismatches). If you change the serving port,
also rebuild `_site` — `site_url` is baked into the search worker URL, and a
port mismatch trips a cross-origin error on every page.

## Syncing upstream

The fork tracks an `upstream` remote and re-syncs by **merge** (not rebase, to
keep the brand commits intact). Conflicts cluster in two places: i18n template
wrapping and the branding edits in the same regions. Resolution rule of thumb:
take upstream for theme internals / i18n / dev tooling; keep ours for branding
(`mewbo.css`, `shadcn/js/*`, SEO/speculation head, three-zone header, brand
footer, sidebar nav-icons, `cloudflare/`, the package identity, and the
release workflow). After resolving: regenerate `base.css` (`bun run build`),
re-lock (`uv lock`), re-run `manage.py integrity --force`, sync the version,
and run the full Playwright suite. Watch for stale `components/...` include
paths and `_`-rebinding left in brand markup outside the conflict hunks.
