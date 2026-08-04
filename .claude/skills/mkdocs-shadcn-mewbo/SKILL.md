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

## Every page opens with a masthead

**From v1.12.0 a page's `# H1` and its first `## H2` are one unit, and the H2 is
the big one.** This inverts what the levels normally mean, so get it wrong and
the page looks broken rather than merely plain.

```markdown
# Get Started

## Introducing Mewbo

Body copy starts here.
```

The H1 renders as a **small accent label** at ~0.85rem naming where the reader
is. It is lifted out of the body into the page header, so it never appears
twice. The first H2 renders as the **page's visual title** at a `clamp()` up to
2.4rem, set 4px under the label so the pair reads as one block.

### The rules, and why each one exists

- **The subtitle H2 is a title, not a sentence. Never more than 4 words, and
  aim for 2.** It is set at ~38px across the full content column, so a
  descriptive phrase wraps to three lines and reads as prose at heading size.
  A whole site was shipped with 9 word subtitles before anyone looked at a
  rendered page. Write a noun phrase with no finite verb and no trailing
  punctuation.
- **It must not restate the H1.** `Skills` then `About skills` wastes the one
  line that says what the page is.
- **Every page needs one.** Without it the page still builds and still renders,
  it just opens with a tiny accent label above ordinary body copy and no title
  at all. There is no warning. Grep for pages whose first heading after the H1
  is not an H2.
- **Two pages must not share a subtitle.** Three `Get Started` pages once
  converged on the same title and a reader could not tell them apart.
- **Short titles collide on anchors far more easily than long ones**, and the
  site builds `strict: true`. Check the page's existing `##`/`###` headings
  before writing one. `Overview` is the usual offender.

### The H1 must be the file's first block

The theme only lifts a **leading** H1 out of the body. Put anything above it,
including an HTML comment, and the heading stays in the body: the page then
renders its own title twice, once as the label and once as body content. This
bites generated pages hardest, because the generator's provenance comment is
the obvious thing to put on line 1. Put the H1 first and the comment after it.

### A `.ms-hero` page is the same masthead, elaborated

A landing page using `<section class="ms-hero" markdown>` states its own title
inside the hero, so the theme hides the generated H1 rather than showing both.
Do not also write a subtitle H2 there.

Inside the hero, **any** heading level is styled as the hero title, because
Markdown cannot put a class on a heading. `.ms-hero__title` still works for a
hero written as raw HTML.

### The table of contents drops the title

Whichever shape the masthead takes, the heading that names the page is omitted
from the On This Page rail, because it is the page's name rather than one of
its sections. Scroll spy reads its heading set off the rail, so the two stay in
step. Nothing to configure.

### If you are restyling the masthead

Two traps, both of which produced shipped regressions:

1. **The prose rules in `base.css` are unlayered and reach (0,1,2)** — for
   example `article p:not(:first-child)` and `article .typography h2`. A bare
   `.my-class { margin: 0 }` at (0,1,0) **loses silently**. Prefix with
   `article` and match their reach. `mewbo.css` is linked after `base.css`, so
   an equal specificity selector wins on source order.
2. **The copy and pager cluster shares the label's row and is 38px tall against
   a 19px label.** It is bottom aligned so it cannot hang past the label into
   the title. Do not take it out of flow to "free up" the row: an out of flow
   cluster overlaps whatever follows, which then forces both the label and the
   title to reserve right padding, which wraps short titles early and reads as
   a stray indent.

## Prose spacing is one scale

Do not reach for a Tailwind spacing utility to space a heading or a block. The
theme declares four steps on `article`, and they are strictly increasing so a
reader can feel how deep a break is:

| token | value | used for |
|---|---|---|
| `--prose-flow` | 1.5rem | one block to the next inside a passage |
| `--prose-topic-gap` | 2rem | before an H4 |
| `--prose-subsection-gap` | 2.5rem | before an H3 |
| `--prose-section-gap` | 3rem | before an H2 |
| `--prose-heading-lead` | 1rem | after **any** heading, before whatever it introduces |

Space after a heading is deliberately much tighter than space before it, so a
heading binds to the content under it. Override the custom property, never the
individual rules.

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

## Accent colour: fill vs text

The theme carries two clay tokens, and the difference is load-bearing:

- `--primary` is a **fill** — button backgrounds, tint washes, indicators.
- `--primary-text` is the same hue **re-tuned to be read as text** on this
  theme's surfaces, and is what links, active navigation entries, the focus
  ring and the tab underline use.

In dark they are the same value; in light `--primary-text` is materially
darker. A single token cannot serve both, because a fill and legible text on
that fill pull lightness in opposite directions — using `--primary` for text
measured 2.6-3.0:1 on the light page, under the 4.5:1 bar.

If you add your own accent-coloured text in `extra_css`, reach for
`var(--primary-text)`. Use `var(--primary)` only for something you fill.

The page masthead's H1 label uses `--primary-text` for exactly this reason.

**Header chrome sits back on purpose.** The brand wordmark, the search
placeholder and the Ask AI label all use `--muted-foreground` rather than
`--foreground`. They read as chrome, not as content, and pure white made them
compete with the page. The Ask AI label alone is nudged one step darker,
because it is the only one sitting on the button's accent tint rather than on
the header background, where the shared grey measured 4.14:1 in light mode.

**Measure a colour over its real backdrop.** Several surfaces here are
`color-mix()` fills that compute to `oklab()`, which a naive rgb parse mangles
into nonsense contrast figures. Composite onto a canvas and read the pixel
back.

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
| Page opens with a tiny accent label and no title | The page has no subtitle H2 under its H1 |
| Page shows its own title twice | Something sits above the H1, so the theme did not lift it out of the body |
| Title wraps to two or three lines | The subtitle is a sentence. Four words maximum, two is the target |
| Title looks indented, or wraps early with space to spare | A restyle reserved right padding for the button cluster. Bottom align the cluster instead |
| Heading floats between its neighbours | Something overrode `--prose-heading-lead`, or set a margin instead of the token |
| A CSS override "did nothing" | It lost on specificity. The prose rules reach (0,1,2); prefix yours with `article` |

**None of the masthead symptoms above fail the build, and none fail a test.**
They are visual only. Look at a rendered page before calling the work done.

## House rules for writing the prose itself

- No em dashes in user-visible copy.
- Say what a thing does before how it is configured.
- Prefer `flowchart LR` for anything wider than it is deep.
- One idea per admonition; they are for asides, not for structure.
