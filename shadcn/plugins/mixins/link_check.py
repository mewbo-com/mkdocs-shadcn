"""Fail the build when a raw HTML reference in the rendered site does not resolve.

MkDocs rewrites markdown links and images per page depth, and `strict: true`
validates them. Neither covers raw HTML: an `<img src=…>`, `<video poster=…>`,
`<source src=…>` or `<a href=…>` written by hand inside a Markdown file passes
through verbatim. A wrong relative prefix therefore 404s in production while
the build stays green.

The failure is easy to write and impossible to spot, because it depends on the
depth of the page it is written on. With `use_directory_urls`, `href="guide/"`
is correct from the site root and wrong from everywhere else: a page at
`topic.md` serves from `/topic/`, so the browser resolves that href to
`/topic/guide/`. The identical markup on the landing page works, which is
exactly why it gets copied onto a deeper page and breaks.

Off unless a site sets `theme.link_check: true`, because consuming the theme
should cost nothing a site did not ask for and this walks every built page.
When on it warns, and raises under `strict`, matching how MkDocs treats its own
link validation.
"""

from __future__ import annotations

import os
import re

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import get_plugin_logger

from shadcn.plugins.mixins.base import Mixin

logger = get_plugin_logger("mixins/link_check")


class HtmlReference:
    """One raw HTML reference, and whether it resolves on disk.

    A directory URL resolves through its `index.html`, and an extensionless
    href may have been written for a page built as `<name>.html`, so three
    candidates satisfy a reference.
    """

    # Absolute, external and in-page references answer to somebody else.
    SKIP_PREFIXES = (
        "http://",
        "https://",
        "//",
        "data:",
        "mailto:",
        "tel:",
        "#",
        "/",
    )

    def __init__(self, raw: str, page_dir: str) -> None:
        self.raw = raw
        self.page_dir = page_dir
        self.path = raw.split("#", 1)[0].split("?", 1)[0]

    @property
    def is_checkable(self) -> bool:
        return bool(self.path) and not self.path.startswith(self.SKIP_PREFIXES)

    @property
    def resolves(self) -> bool:
        base = os.path.normpath(os.path.join(self.page_dir, self.path))
        return any(
            os.path.exists(candidate)
            for candidate in (
                base,
                os.path.join(base, "index.html"),
                base + ".html",
            )
        )


class RenderedSite:
    """The built site, walked once and checked for unresolved references."""

    # `src` and `poster` carry media, `href` carries navigation. All are
    # emitted verbatim from raw HTML and none is validated by strict mode.
    ATTRIBUTES = re.compile(r'\b(?:src|poster|href)="([^"]+)"')

    def __init__(self, site_dir: str) -> None:
        self.site_dir = site_dir

    def _pages(self):
        for page_dir, _subdirs, names in os.walk(self.site_dir):
            for name in names:
                if name.endswith(".html"):
                    yield page_dir, os.path.join(page_dir, name)

    def unresolved(self) -> list[str]:
        misses: set[str] = set()
        for page_dir, page in self._pages():
            with open(page, encoding="utf-8", errors="ignore") as handle:
                html = handle.read()
            for raw in self.ATTRIBUTES.findall(html):
                ref = HtmlReference(raw, page_dir)
                if ref.is_checkable and not ref.resolves:
                    rel = os.path.relpath(page, self.site_dir)
                    misses.add(f"{rel}: {raw}")
        return sorted(misses)


class LinkCheckMixin(Mixin):
    """Resolve every relative src, poster and href in the built site."""

    def on_post_build(self, config: MkDocsConfig) -> None:
        # Chain FIRST, and unconditionally. Every mixin here cooperates through
        # `Mixin._super_method_or`, and the search plugin at the end of the MRO
        # writes `search_index.json` from its own `on_post_build`. Returning
        # early without delegating silently shipped a site whose search worker
        # fetched a file that was never written, which surfaces as a JSON parse
        # error in the browser and nowhere in the build.
        result = super().on_post_build(config)
        if not config.theme.get("link_check", False):
            return result
        # Checked after the chain, so the artifact being inspected is finished.
        misses = RenderedSite(config["site_dir"]).unresolved()
        if not misses:
            return result
        listing = "\n  ".join(misses)
        message = (
            f"{len(misses)} raw HTML reference(s) do not resolve. MkDocs does "
            f"not rewrite or validate these:\n  {listing}"
        )
        if config.get("strict"):
            raise SystemExit(f"link_check: {message}")
        logger.warning(message)
        return result
