---
name: mkdocs-shadcn-mewbo
description: Use when writing or reviewing documentation for a site built with the mkdocs-shadcn-mewbo theme - authoring Markdown pages, configuring mkdocs.yml, adding diagrams, tabs, code blocks, tooltips, media or API references, or diagnosing why one of those renders wrong. Triggers on "mkdocs", "docs site", "theme: shadcn", mkdocs.yml, a mermaid or admonition or content-tab block, and on any .md file in a docs/ tree for such a site.
---

# Authoring for mkdocs-shadcn-mewbo

An opinionated fork of `mkdocs-shadcn`. It diverges from both its upstream and
from mkdocs-material in ways that change what you write, so **do not assume
mkdocs-material syntax works here** — several of its headline features are its
own theme JavaScript and are deliberately not implemented.

This file is self-contained. You do not need the theme's source to author for it.

## The one thing that breaks everything

**Features only render if the matching Markdown extension is enabled.** A
missing extension is silent: the block renders as plain text or a code fence,
with no warning in the build. If a diagram, tab set or fence title "does
nothing", check `markdown_extensions:` before anything else.

Minimum viable `mkdocs.yml` for this theme:

```yaml
theme:
  name: shadcn

plugins:
  - search          # this theme's SearchPlugin; templates need its filters

markdown_extensions:
  - admonition
  - footnotes
  - extra           # bundles attr_list, abbr, md_in_html, tables, def_list
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
  - pymdownx.highlight:
      use_pygments: true
      css_class: codehilite     # keep: the theme's CSS and copy button select on it
      anchor_linenums: true
      line_spans: __span
      pygments_lang_class: true
  - pymdownx.inlinehilite
  - pymdownx.tabbed:
      alternate_style: true     # required; the theme styles this markup
  - pymdownx.blocks.details
  - pymdownx.blocks.tab
  - pymdownx.blocks.caption
  - pymdownx.keys           # ++ctrl+shift+a++ renders real <kbd> elements
  - pymdownx.snippets
  - shadcn.extensions.iconify
  - shadcn.extensions.hover_card
```

**Pygments must be installed.** The theme sets `use_pygments: true` and ships
Pygments stylesheets, and `pymdownx.highlight` DEGRADES SILENTLY without the
package: code blocks lose highlighting, fence titles and line numbers all at
once, with no error to point at. It is a declared dependency from v1.10.0; on
anything older, add `pygments` to your own docs dependencies.

`plugins: - search` is **not optional**. It is this fork's `SearchPlugin`
subclass, and the theme's templates call filters it registers (`iconify`,
`scoped_nav`, `read_file`). Without it the build fails with
`No filter named 'iconify'`.

## Writing content

### Code blocks

Titles, line numbers and highlighted lines all work, and all are styled:

````markdown
```python title="app.py" linenums="1" hl_lines="2 3"
def load(path):
    with open(path) as fh:
        return fh.read()
```
````

- `title="…"` renders a header strip on the block's top edge.
- `linenums="1"` adds a deep-linkable line-number gutter.
- `hl_lines="2 3"` tints those lines.
- Inline: `` `#!python x = 1` `` highlights inline code (needs `inlinehilite`).
- A copy button is added to every block automatically. Do not write one.

### Diagrams

A ```` ```mermaid ```` fence becomes a framed figure with an **Expand** control
that opens a zoom-and-pan viewer. Diagrams are drawn from the site's own colour
tokens and typeface and follow the light/dark toggle without a reload.

Two things worth knowing when authoring:

- **Direction is yours, not the theme's.** `flowchart LR` vs `TD` is a token in
  your source and nothing in the theme can override it. Prefer `LR` for wide,
  shallow flows — it reads better in a documentation column.
- The inline card **fits** the diagram to the column; it only falls back to
  horizontal scrolling when a diagram is nearly three times the column width.
  Expand is where a large diagram is meant to be read, so do not fight the
  preview size.
- Force a label break with `<br/>`; long labels wrap on their own.

### Content tabs

```markdown
=== "Python"
    Indented four spaces.

=== "TypeScript"
    Also four spaces.
```

Supported up to **24 tabs** per set. Past that the set silently selects nothing
— if you need more, you are writing a table, not tabs.

### Admonitions and details

```markdown
!!! note "Optional title"
    Indented content.

/// details | Click to expand
Collapsed by default.
///
```

### Tooltips

Define once, applies everywhere the term appears, and the term gets a dotted
underline so readers know to hover:

```markdown
The HTML spec.

*[HTML]: HyperText Markup Language
```

This is the browser's own tooltip — keyboard- and screen-reader-accessible.
For **rich, positioned** hover content the theme has its own hover card:

```markdown
[trigger text]^[hover card content, which may be a sentence or two]
```

### Keyboard shortcuts

Write shortcuts as `++key+key++`. They render as real `<kbd>` elements, so
they read as keys rather than as code or as prose:

```markdown
Press ++ctrl+shift+a++ to open the panel.
Press ++cmd+k++ on macOS or ++ctrl+k++ elsewhere to search.
```

Both platforms are covered: `cmd` and `opt` render the macOS Command and
Option keys, `windows` renders the Windows key. Also available: `ctrl`,
`shift`, `alt`, `enter`, `tab`, `esc`, `space`, `backspace`, `delete`,
`arrow-up` / `arrow-down` / `arrow-left` / `arrow-right`, and the function
keys.

**Do not write shortcuts as inline code or plain text.** `` `Ctrl+Shift+A` ``
renders as a code span, which means something different, and plain text gets
no visual treatment at all. When a shortcut differs across platforms, give
both rather than picking one.

### Media

- **Carousels** (`.swiper.ms-shots`, needs `theme.carousel: true`) size their
  box to **16:9** from v1.10.1. Do not override `aspect-ratio` in your own
  `extra_css`; a non-16:9 image is still protected by `object-fit: contain`.
- **Images** get a matte frame automatically. Opt out with `{ .no-border }`
  (needs `attr_list`) for logos and badges that must bleed.
- **Video** autoplays while on screen and pauses when scrolled away. Write a
  plain `<video src="…" width="…"></video>`; the theme mutes it, makes it
  inline and loops it. Add `data-no-autoplay controls` for a clip with
  meaningful audio. Reduced-motion readers get controls instead of playback.
  **Paths are relative to the built page**, not the source file — with
  directory URLs, a page at `guide.md` serves from `/guide/`, so an asset at
  `docs/assets/x.mp4` is `../assets/x.mp4`.

### Tables

Cells wrap by default; wide tables reflow rather than scrolling. Add
`class="nowrap"` to a cell that must stay on one line. The first column has a
minimum width so row labels stay legible.

If `theme.sortable_tables: true`, prose tables with a header and more than one
row become click-to-sort. Opt one out with `data-no-sort`.

### Code and API references

Two link schemes render as inline badges when `theme.code_refs` is configured:

```markdown
[the loop](repo:packages/core/loop.py#L20-L48)
[POST /api/sessions](endpoint:POST /api/sessions)
```

`repo:` links to the file at the built commit; `endpoint:` links into the REST
reference page and is tinted by method. Both are left as plain links when the
feature is off, so they are safe to write either way.

## Theme options

Every key below sits under `theme:` in `mkdocs.yml`. Defaults shown.

| Key | Default | What it does |
|---|---|---|
| `icon` | `null` | Site icon (favicon falls back to it) |
| `show_title` | `true` | Show the site name in the header |
| `hide_source_files` | `false` | Hide the "view source" affordance |
| `show_stargazers` | `true` | Live star count from `repo_url` |
| `pygments_style.light` / `.dark` | `shadcn-light` / `github-dark` | Syntax theme per mode |
| `topbar_sections` | `false` | Top-level nav sections in the header |
| `katex_options` | `null` | Passed to KaTeX when arithmatex is on |
| `show_datetime` | `false` | Page updated timestamp |
| `accent` | `null` | Override the accent colour |
| `ai.deepwiki_repo` | `null` | **On/off switch for the whole Ask AI panel.** `owner/name` |
| `ai.question_prefix` | `null` | Text prepended to every Ask AI question |
| `ai.examples` | `[]` | Example questions in the Ask AI empty state |
| `nav_icons` | `{}` | Map nav titles to Iconify slugs, e.g. `Guides: lucide:compass` |
| `versions_root` | `null` | Root for the version switcher |
| `footer.tagline` / `.docs` / `.sections` / `.social` / `.copyright` / `.show_attribution` | — | Footer composition |
| `show_version_switcher` | `false` | Version dropdown (needs `mike`) |
| `show_build_info` | `false` | Build metadata in the footer |
| `carousel` | `false` | Loads Swiper for `.swiper.ms-shots` galleries |
| `sortable_tables` | `false` | Loads Tablesort; prose tables become sortable |
| `header_tabs` | `null` | Header tab rail; each entry takes `label`, `icon`, `url`, optional `section` and `match:` prefixes |
| `code_refs` | `null` | Enables `repo:` / `endpoint:` badges |

## How this fork differs from mkdocs-material

Authors coming from Material reach for features that are **not here**, because
they are Material's own theme JavaScript rather than Markdown extensions:

| Material feature | Here |
|---|---|
| Code annotations (`(1)` markers) | **Not implemented.** Needs Material's popover runtime. Use a numbered list under the block. |
| "Improved" styled tooltips | **Not implemented.** `abbr` gives the native tooltip; the hover card covers rich content. |
| Linked/synced content tabs | **Not implemented.** Tabs switch independently. |
| Animated tab indicator, tab overflow arrows | Not implemented; tabs wrap instead. |
| `content.code.select` | Not implemented. |
| Instant navigation (`document$`) | Not present — **do not write `document$.subscribe`**; use `DOMContentLoaded`. |

What this fork adds that neither upstream nor Material has: the Ask AI panel,
`repo:`/`endpoint:` code-reference badges, positioned hover cards, the
three-zone header with a tab rail, the `.ms-*` media kit (`.ms-shot`,
`.ms-devices`, `.ms-shots`), in-viewport video autoplay, and the mermaid
Expand viewer.

## When something renders wrong

| Symptom | Almost always |
|---|---|
| Mermaid fence shows as highlighted source | `pymdownx.superfences` custom_fence for mermaid is missing |
| Fence `title=` prints as text, or no line numbers | `pymdownx.highlight` not enabled, or `css_class` is not `codehilite` |
| Tabs render as stacked headings | `pymdownx.tabbed` missing, or `alternate_style: true` not set |
| A tab past the eighth shows nothing | You exceeded the 24-tab ceiling, or the theme predates v1.9.0 |
| `No filter named 'iconify'` at build | `plugins: - search` is missing |
| Search works in production, breaks on preview | Theme older than v1.9.1 |
| `og:site_name` absent / WebMCP tool named `search_docs` | Theme older than v1.9.1 |
| Abbreviation shows no underline | Term does not exactly match the `*[TERM]:` definition, including case |
| Video does not play | Path is relative to the built URL, not the source file |
| Diagram is tiny | Expected — the card is a preview; use Expand |
| Code blocks unhighlighted AND no titles AND no line numbers, all at once | Pygments is not installed |
| Build dies with `'NoneType' object has no attribute 'get'` | `arithmatex` enabled against a theme older than v1.10.0; set `theme.katex_options: {}` |
| `++ctrl+k++` prints literally | `pymdownx.keys` is not enabled |

## House rules for writing the prose itself

- No em dashes in user-visible copy.
- Say what a thing does before how it is configured.
- Prefer `flowchart LR` for anything wider than it is deep.
- One idea per admonition; they are for asides, not for structure.
