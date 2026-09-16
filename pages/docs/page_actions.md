---
title: Page actions
summary: The Copy page split button, and the menu of source and assistant links behind it
---

## What the control does

Every page carries a split button at the top right. The left half copies the
page's Markdown; the chevron opens the rest.

| Item | What it does |
|---|---|
| Copy page | Copies this page's Markdown source to the clipboard. |
| View as Markdown | Opens the page's raw `.md` on your repo host. |
| Open in ChatGPT | Opens ChatGPT with a one-line prompt naming that file. |
| Open in Claude | The same, for Claude. |

Copy is the common case, so it stays one click. The other three exist because
a reader who wants to ask an assistant about a page should not have to
copy-paste the whole thing into a chat window.

## What gets sent to an assistant

One sentence naming the page's source URL — never the page's text:

```text
Read https://raw.githubusercontent.com/acme/widgets/refs/heads/main/docs/install.md so I can ask questions about it.
```

A prompt carrying a whole document makes a fragile URL, and it goes stale the
moment the page changes. A URL is re-fetched when the reader actually asks.

## Configuration

The three source-backed items need a public URL for the page's Markdown, so
they appear only when the site sets `repo_url`. Without one, this renders as
the plain copy button it has always been — no dead controls.

```yaml
repo_url: https://github.com/acme/widgets
```

The branch comes from the checkout the docs build from. Set `source_ref` when
the branch you **build** from is not the branch your repo **publishes** — a
private working branch mirrored to a public repo under another name, say —
because the local branch name is then not a ref the public URL can use:

```yaml
theme:
  name: shadcn
  source_ref: current
```

An `edit_uri` you set yourself takes precedence, since that is mkdocs' own way
of saying the same thing. mkdocs' *invented* default does not: when a site
sets only `repo_url`, mkdocs fills `edit_uri` with a hardcoded
`edit/master/docs/`, which produces a 404 on every repo not published from
`master`. The theme recognises that default and ignores it.

To hide the control entirely:

```yaml
theme:
  hide_source_files: true
```
