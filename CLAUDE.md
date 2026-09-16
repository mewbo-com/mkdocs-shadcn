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
  `plugins/mixins/*` (i18n, git, dev, order, mkdocstrings, katex, code_refs,
  table, markdown). The `TableMixin` wraps every `<table>` in
  `<div class="table-wrapper">` via `on_page_content`.
- `shadcn/js/*.js` — theme + Mewbo enhancement scripts.
- Brand content components live in `mewbo.css` as the `.ms-*` kit: the landing
  hero/cards plus `.ms-shot` (frameless screenshot with a bottom caption overlay),
  `.ms-devices` (matched-height mockup pair, ratios via `--ms-devices-*`), and
  `.ms-shots` (Swiper carousel). The carousel is gated by `theme.carousel`,
  which makes `main.html` emit the Swiper CDN + `js/carousel.js`; a consumer
  writes only `.swiper.ms-shots` markup. These were consolidated from consumer
  repos so docs sites get them without forking. `theme.lightbox` is the
  parallel gate for the fullscreen viewer (Viewer.js CDN + `js/lightbox.js`,
  styled by the `.ms-viewer` block in `mewbo.css`); it needs no markup at all,
  since the script picks up every eligible content image.
- `pages/` — the demo/docs site (`pages/mkdocs.yml`); `tests/` — Playwright.
- `internal/` + `manage.py` — dev tooling (not shipped in the wheel).

## Conventions & gotchas (learned the hard way)

- **The carousel must not drop clicks (`shadcn/js/carousel.js`).** Swiper's
  `loopPreventsSliding` defaults to **true**, which silently discards any
  `slideNext`/`slidePrev`/`slideToLoop` issued while a transition is running.
  With `loop: true` and a 300ms transition that means a reader clicking an
  arrow or a dot at a normal pace loses most of their clicks and the carousel
  reads as *stuck* — measured 4 of 12 rapid clicks landing, 12 of 12 with the
  option off. It is set `false` deliberately; do not let a re-sync restore the
  default. Autoplay is `disableOnInteraction: true` for the same reason: it
  must retire once the reader takes over instead of moving the slide under
  them between clicks. `tests/test_carousel_navigation.py` clicks at 120ms and
  fails if a single click is swallowed or a dot disagrees with the slide.
- **The fullscreen viewer is Viewer.js, and its footer must measure ZERO
  (`shadcn/js/lightbox.js`).** Viewer.js sizes the image against
  `container.height - footer.offsetHeight`, reading that `offsetHeight` off
  the element **directly** — so `position: absolute` on `.viewer-footer` is
  NOT enough to stop it reserving that strip, and the picture is held short by
  exactly the footer's height (65px; an 844x390 landscape phone was capped at
  78% of the size it could show). The cure is the zero-height `.viewer-footer`
  rule in `mewbo.css` with its children floated and `pointer-events` handed
  back per child. That is what lets `ImageViewer.COVERAGE = 1` mean the whole
  screen. Viewer.js clamps to natural size itself (`Math.min(o*n, t)`), so
  full size still never means upscaled-into-blur.
  - Its gallery comes from a **detached `<ul>`** (`GallerySource`), not from
    live carousel markup: pointing the library at `.swiper` would feed it
    Swiper's clones and its DOM reordering. Dedupe by `src` stays essential.
  - The predecessor was GLightbox, whose `INSET_X`/`RESERVE_Y`/`MAX_EDGE`
    budget subtracted a flat 200px of height for chrome laid out *beside* the
    image. Those tokens are gone; do not reintroduce them.
- **Tables word-wrap by default.** `tailwind/table.css` deliberately does NOT
  put `whitespace-nowrap` on `th`/`td` (it uses `break-words`); the
  `.table-wrapper` keeps `overflow-x:auto` only as a fallback for un-wrappable
  content. Do not reintroduce `nowrap` — `tests/test_browser.py::`
  `test_tables_wrap_no_horizontal_scroll` (fixture: `pages/docs/`
  `table_wrap_regression.md`) fails if cells compute to `white-space:nowrap` or
  a table overflows horizontally. Use `class="nowrap"` to opt a cell out. The
  first column gets `min-width: 12rem` (`table tr > :first-child`) so row labels
  don't collapse to one word per line — a *min-width*, not `nowrap`, so the
  regression test stays green.
- **Brand identity comes from `config.site_name`, never a hardcoded "Mewbo".**
  The page `<title>` (`seo.html`), the Ask-AI greeting + avatar (`search.html`),
  and the WebMCP tool name (`webmcp.js`, which reads the `og:site_name` meta
  `seo.html` already emits) all derive from `site_name`, so a consumer site
  shows its own name with zero template forks. A re-sync that reintroduces a
  literal `"Mewbo"` in those three is a regression — keep them `site_name`-driven.
- **`mewbo.css` is unlayered; `base.css` utilities live in `@layer`.** Unlayered
  rules beat layered ones regardless of specificity, so `mewbo.css` overrides
  Tailwind utility classes (e.g. the compact full-width sidebar over
  `p-2`/`h-8`/`gap-1`/`lg:w-fit`) **without `!important`**. The exception is
  Tailwind's `!`-utilities (e.g. `group-data-[collapsible=icon]:size-8!`), which
  emit `!important` and still win — only reach for `!important` to beat those.
- **Tabs: style both markups.** `tailwind/tabs.css` covers the legacy adjacency
  markup *and* `pymdownx`'s `alternate_style: true` (`.tabbed-alternate` with
  `.tabbed-labels` / `.tabbed-block`). The alternate rules are positional
  (`input:nth-of-type(N):checked ~ …:nth-child(N)`) and capped at 8 tabs —
  extend the two nth-lists if a group needs more. Alternate panels render dead
  without these.
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
- **Code-reference badges (`theme.code_refs`, v1.4.0).** The `CodeRefsMixin`
  rewrites markdown links with two custom URI schemes into inline pills in
  `on_page_content`: `repo:<path>#L1-L9` → octicon file badge, `endpoint:GET
  /path` → method-tinted badge. It runs *after* markdown rendering, so refs
  inside fenced code blocks (not anchors) survive verbatim. Disabled unless
  `theme.code_refs` is non-null. **Nothing is hardcoded to a consumer**: the
  file-badge base URL derives from `config.repo_url` (`/blob/<sha>/…`, SHA from
  git with a configurable `default_ref` fallback), and endpoint badges only
  activate with `theme.code_refs.endpoint` (a `reference_page` + a path-prefix→
  tag map) — the endpoint href is resolved *relative to the current page* via
  `mkdocs.utils.get_relative_url`, so any nav depth works. Styling lives in
  `shadcn/css/code-refs.css`, `<link>`'d only when the feature is on (head.html
  gates it). No JS, so no SRI; no Tailwind, so no `base.css` rebuild.
- **Icons resolve at BUILD time, so `api.iconify.design`'s rate limiter is a
  build dependency** (`shadcn/iconify.py`). The per-icon `/{prefix}/{name}.svg`
  endpoint throttles a shared egress IP hard, which is what a CI runner has: a
  consumer with ~45 nav icons made ~50 sequential requests, got `429` for most
  of them, and every 429 was an `ERROR` that aborted `--strict`. The cure is
  the **batch** endpoint `/{prefix}.json?icons=a,b,c`, one request per icon
  *set*; `IconCache.warm()` is called from `on_config` with the whole census so
  nothing resolves lazily. **The two endpoints are metered separately** —
  measured 2026-09-14, the `.svg` endpoint returned 429 while `.json` returned
  200 from the same address in the same second — which is why batching fixes
  this and retrying alone does not. Results also persist under the site's
  `.cache/iconify/`, so a warm rebuild makes zero requests.
  - **A name the API positively reports as absent stays a hard `ERROR`**, since
    that is a typo in the consumer's own config and a warning would ship a
    blank square. Throttling and outages degrade to an `<iconify-icon>` the
    browser resolves instead, because the runtime script is always loaded.
  - **Width is scaled by aspect ratio and rounded UP to 2dp** (`256x153` at
    `16px` is `26.78px`, not `26.77`). `round()` is wrong and is invisible on a
    square icon, which is nearly all of them.
  - **The mirrors `api.simplesvg.com` / `api.unisvg.com` are NOT usable
    fallbacks** — both answer `403 Cloudflare` to every request, browser
    user-agent included. Do not add them as a retry target.
  - `THEME_ICONS` lists the names the theme's own templates hardcode. A name
    added to a template belongs there too, or it resolves one-at-a-time.
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
