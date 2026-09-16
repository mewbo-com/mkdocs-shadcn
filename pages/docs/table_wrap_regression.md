---
title: Table wrap regression
summary: Regression fixture — tables must word-wrap, never force horizontal scroll
---

This page is a regression fixture for the table word-wrapping bug. It
exists solely to verify that long cell content wraps inside table cells
and never causes a horizontal scrollbar (root cause: `whitespace-nowrap`
on `th`/`td` combined with `.table-wrapper { overflow-x: auto }`).

## Wrapping under pressure

Five wide columns, so every one of them has to wrap. `test_sortable_tables`
takes the page's FIRST table, so this one stays first — its rows are not in
alphabetical order, which is what lets that test assert a header click
actually reordered them.

| Component name and category | Detailed description of the behaviour under normal operating conditions | Configuration key used in mkdocs.yml | Default value and accepted range of inputs | Notes for future maintainers and theme contributors |
|---|---|---|---|---|
| Navigation sidebar section renderer | Automatically collapses nested entries deeper than two levels and applies an animated chevron indicator when the user expands a section by clicking the header label | `theme.topbar_sections` | `false`; accepts `true` or `false` only | When set to `true` the top-level sections move into the top bar and the sidebar shows only the current section's children |
| Syntax highlighting engine integration | Delegates code block rendering to Pygments using the configured light and dark theme names, falling back to a plain `<pre>` block when the requested style is not installed on the build machine | `theme.pygments_style.light` and `theme.pygments_style.dark` | `shadcn-light` / `github-dark`; any valid Pygments style name is accepted | Custom Pygments styles must be registered as entry-points under `pygments.styles` before they can be referenced here |
| KaTeX mathematics renderer options | Passes a freeform options object directly to the KaTeX `renderMathInElement` call, enabling advanced features such as macro definitions and trust overrides for `\htmlStyle` commands in equations | `theme.katex_options` | `{}`; see KaTeX documentation for the full list of supported keys and their types | The `trust` key must be set to `true` before any `\htmlStyle` or `\url` macros will render without an error in the browser console |
| ECharts alpha extension block processor | Parses fenced code blocks labelled `echarts` and converts them to interactive chart widgets powered by Apache ECharts, injecting the required JavaScript bundle only on pages that contain at least one chart block | `shadcn.extensions.echarts.alpha` (no sub-keys) | Enabled by presence in `markdown_extensions` list; no further configuration options are exposed at this time | This extension is marked alpha and its block syntax may change in a future release without a deprecation period |

## Leading in wrapped cells

The ordinary docs shape, and the one the five-column table above is too
extreme to represent: two columns, a short label and a prose cell long enough
to wrap, with inline `code` chips in the wrapped run. A chip's own vertical
padding eats into the gap between lines, so consecutive lines of chips are
where tight leading shows first. Fixture for
`test_table_cells_have_prose_leading`.

| Platform | Requirement |
|---|---|
| Linux | `git` ≥ 2.30, `tmux` ≥ 3.0 |
| macOS | `git` (Xcode CLT), `tmux` (`brew install tmux`) |
| Windows | WSL2 with the above. Windows-native runs only the non-tmux subcommands (`grove version`, `grove config show`, `grove debug`). The TUI needs WSL. |
