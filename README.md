
![banner](./.github/assets/banner.png)

# mkdocs-shadcn-mewbo

> [!IMPORTANT]
> This is **mewbo-com's brand fork** of [`asiffer/mkdocs-shadcn`](https://github.com/asiffer/mkdocs-shadcn). It bakes in the Mewbo brand chrome (cream/clay palette, three-zone header, sidebar nav-icons, ToC rail, mobile nav sheet, dual-mode Search + Ask AI modal, full SEO + Speculation Rules prefetch) so every product under the mewbo-com umbrella consumes a single dependency instead of copy-pasting overrides per repo.
>
> The theme entrypoint is still `theme: shadcn` — only the pip package name changes (`mkdocs-shadcn` → `mkdocs-shadcn-mewbo`).
>
> The original `mkdocs-shadcn` is an unofficial port of shadcn/ui to MkDocs and is not affiliated with [@shadcn](https://twitter.com/shadcn).

## Install

This fork is **not published to PyPI**. Every push produces a downloadable wheel attached to a GitHub Release; consumers pin to either a stable version tag or to the exact commit a feature branch is on.

### Pin to a stable tag (recommended for shipping consumers)

```toml
# pyproject.toml
[project]
dependencies = [
    "mkdocs-shadcn-mewbo @ https://github.com/mewbo-com/mkdocs-shadcn/releases/download/v1.0.0/mkdocs_shadcn_mewbo-1.0.0-py3-none-any.whl",
]
```

### Pin to a specific commit (use this while a feature branch is in flight)

Every branch push triggers a workflow that builds a wheel named `mkdocs_shadcn_mewbo-<base>+<short-sha>-py3-none-any.whl` and attaches it to a `commit-<short-sha>` pre-release:

```toml
# pyproject.toml — pinned to commit abc1234 of any branch
[project]
dependencies = [
    "mkdocs-shadcn-mewbo @ https://github.com/mewbo-com/mkdocs-shadcn/releases/download/commit-abc1234/mkdocs_shadcn_mewbo-1.0.0+abc1234-py3-none-any.whl",
]
```

The exact URL is surfaced in the workflow run's job summary, or via:

```shell
gh release view commit-abc1234 --repo mewbo-com/mkdocs-shadcn --json assets -q '.assets[] | select(.name | endswith(".whl")) | .url'
```

### Or pin via VCS (no wheel download — pip/uv build at install time)

```toml
[project]
dependencies = [
    # by tag
    "mkdocs-shadcn-mewbo @ git+https://github.com/mewbo-com/mkdocs-shadcn.git@v1.0.0",
    # by branch (uv resolves to a SHA in uv.lock)
    # "mkdocs-shadcn-mewbo @ git+https://github.com/mewbo-com/mkdocs-shadcn.git@master",
    # by exact commit
    # "mkdocs-shadcn-mewbo @ git+https://github.com/mewbo-com/mkdocs-shadcn.git@abc1234abc1234abc1234abc1234abc1234abcd",
]
```

Then in `mkdocs.yml`:

```yaml
theme:
  name: shadcn
  ai:
    deepwiki_repo: my-org/my-product   # enables Ask AI panel
    question_prefix: |                  # optional: product aliases / tone
      Give product-first, well-grounded answers.
  nav_icons:                            # optional sidebar icons (Iconify slugs)
    Home: lucide:house
    "Get Started": lucide:rocket
  versions_root: my-product             # optional: github.io/<my-product>/<version>/
  header_tabs:                          # optional second header row (tab rail)
    - label: Documentation
      icon: lucide:book-open            # optional Iconify slug
      url: .                            # site-root-relative; "."/"" = docs root
    - label: API Reference
      icon: lucide:braces
      url: rest-api/
      section: API Reference            # scope the sidebar to this nav Section
      match:                            # extra prefixes that also activate the tab
        - reference/
```

Two per-item keys refine the rail:

- **`section`** (exact top-level nav Section title) scopes the left sidebar to the tab. On any page inside the named Section the sidebar shows only that Section's children; on every other (root-tab) page it shows the full nav minus all claimed Sections. It activates as soon as one tab declares it, and when set it takes precedence over `topbar_sections`.
- **`match`** (list of site-root-relative url prefixes) adds prefixes that also activate the tab, normalized exactly like `url`. Use it when one tab fronts several top-level url trees. First-match-wins across tabs and the root fallback stay unchanged.

Two opt-in layout features ship with the theme:

- **`header_tabs`** — a horizontal tab rail fused to the bottom of the sticky header (icon + label items, accent underline on the active tab). Null/absent emits zero markup, so existing consumers are unaffected.
- **`template: app.html`** (page front matter) — a full-bleed page template: no sidebar, no ToC, no article wrapper, no footer — just the brand header (+ tab rail) over a single `<main>` that fills the viewport and scrolls internally. Made for embedding full-page apps (e.g. a Scalar API reference) under the shared header.

## Releasing

> [!NOTE]
> Because this repo is a fork, GitHub disables Actions on the first clone. After enabling Actions in the repo settings, the **first** workflow run must be triggered manually (`gh workflow run release.yaml --ref <branch>`); subsequent pushes auto-trigger the workflow as configured.

The release workflow (`.github/workflows/release.yaml`) runs in two modes:

| Trigger | Release tag | Wheel name | Marked |
|---|---|---|---|
| Push of a `v*` tag | `vX.Y.Z` | `mkdocs_shadcn_mewbo-X.Y.Z-py3-none-any.whl` | normal |
| Any other push (branch, dispatch) | `commit-<short-sha>` | `mkdocs_shadcn_mewbo-X.Y.Z+<sha>-py3-none-any.whl` | **pre-release** |

Every commit therefore has its own pinnable artifact — consumers can bump to a feature-branch commit before the official tag exists, then switch to the tag wheel once it's cut.

To cut an official release:

```shell
# bump pyproject.toml `version = "X.Y.Z"`, commit, then:
git tag v1.0.1
git push origin v1.0.1
```

The workflow refuses to publish if the tag and `pyproject.toml` version don't agree — you cannot accidentally ship a mislabelled wheel. For commit builds, the `pyproject.toml` version is rewritten in CI to `<base>+<short-sha>` (PEP 440 local segment) before `uv build`, so each commit's wheel is uniquely cacheable. Each run's job summary surfaces the exact `pyproject.toml` snippet to paste into a consumer.

## Cloudflare Worker (agent discoverability)

Every Mewbo umbrella product gets the same `.well-known/` scaffold (`api-catalog`, `mcp/server-card.json`, `agent-skills/index.json`) plus RFC 8288 `Link:` headers via a product-neutral worker shipped under [`cloudflare/`](./cloudflare/README.md). Configure via `wrangler.toml [vars]`; the worker JS itself never needs editing per-product.

## Documentation

The original theme's documentation (still valid for everything except the brand chrome / theme config keys this fork adds) lives at [asiffer.github.io/mkdocs-shadcn](https://asiffer.github.io/mkdocs-shadcn/). The fork-specific theme config keys (`ai.deepwiki_repo`, `ai.question_prefix`, `ai.examples`, `nav_icons`, `versions_root`, `show_version_switcher`, `show_build_info`, `header_tabs`) are documented inline in `shadcn/mkdocs_theme.yml`.

> [!NOTE]
> Upstream notes that [MkDocs is stale](https://fpgmaas.com/blog/collapse-of-mkdocs/) and suggests [ProperDocs](github.com/ProperDocs/properdocs) as a drop-in replacement.

## Extensions

The theme tries to support the built-in extensions along with some `pymdownx` ones. 

- [x] [`admonition`](https://python-markdown.github.io/extensions/admonition/)
- [x] [`codehilite`](https://python-markdown.github.io/extensions/code_hilite/)
- [x] [`fenced_code`](https://python-markdown.github.io/extensions/fenced_code_blocks/)
- [x] [`footnotes`](https://python-markdown.github.io/extensions/footnotes/)
- [x] [`pymdownx.tabbed`](https://facelessuser.github.io/pymdown-extensions/extensions/tabbed/)
- [x] [`pymdownx.blocks.caption`](https://facelessuser.github.io/pymdown-extensions/extensions/blocks/plugins/caption/) 
- [x] [`pymdownx.blocks.details`](https://facelessuser.github.io/pymdown-extensions/extensions/blocks/plugins/details/) 
- [x] [`pymdownx.blocks.tab`](https://facelessuser.github.io/pymdown-extensions/extensions/blocks/plugins/tab/) 
- [x] [`pymdownx.progressbar`](https://facelessuser.github.io/pymdown-extensions/extensions/progressbar/)
- [x] [`pymdownx.arithmatex`](https://facelessuser.github.io/pymdown-extensions/extensions/arithmatex/)
- [x] builtin [`shadcn.echarts`](https://asiffer.github.io/mkdocs-shadcn/extensions/echarts/)
- [x] builtin [`shadcn.iconify`](https://asiffer.github.io/mkdocs-shadcn/extensions/iconify/)
- [x] builtin [`shadcn.codexec`](https://asiffer.github.io/mkdocs-shadcn/extensions/codexec/) 


## Plugins

- [x] builtin [`excalidraw`](https://excalidraw.com/) - With this plugin, you can directly edit your excalidraw scene in dev mode (kind of WYSIWYG) while it is rendered as svg at build time.
- [x] [`mkdocstrings`](https://mkdocstrings.github.io/) - a MkDocs plugin for auto-generating API documentation from docstrings. (alpha)
- [x] taylor-made `autonumber` plugin to automatically number and reference some elements (figures, tables, equations...)

## Developers

This project is open to contributions. In general, we need to apply the shadcn/ui style to already existing plugins or extensions. 

We recently release the css sources we use to style the theme. It mainly uses [`tailwindcss`](https://tailwindcss.com/).

### Setup

First clone the repo:
```shell
git clone https://github.com/asiffer/mkdocs-shadcn
cd mkdocs-shadcn
```

Then you can install python dependencies ([`uv`](https://docs.astral.sh/uv/) required):
```shell
uv sync --all-extras
```

Finally, you can install tailwind with your favourite package manager (npm, yarn, bun, etc.):

```shell
bun install
```

### Dev mode

We use the project pages to as a test project for this theme. You can run the local server in the `pages/` subdirectory.

```shell
cd pages/
uv run mkdocs serve --watch-theme -w ..
```

In parallel, you are likely to run the tailwind watcher to compile the css sources. In the root folder:

```shell
bun dev
```

### Testing

Tests are managed by [`pytest`](https://docs.pytest.org/en/stable/) and are located in the [tests/](./tests/) folder.

Currently we only test that there is no browser issue through [playwright](https://playwright.dev/).