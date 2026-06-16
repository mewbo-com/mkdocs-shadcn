"""Code-reference badge rendering, as an ``on_page_content`` mixin.

Authors write standard markdown links with two custom URI schemes:

- ``[<label>](repo:<repo-relative-path>#L<start>-L<end>)`` — a file reference.
  The ``#L<start>-L<end>`` fragment is optional (a single ``#L<start>`` line or
  no fragment are both accepted). Renders an octicon badge linking to the file
  in the project repo at the build commit, with a right cell showing the line
  range.

- ``[<label>](endpoint:<METHOD> <path>)`` — a REST endpoint reference, e.g.
  ``[POST /api/sessions](endpoint:POST /api/sessions)``. Renders a
  method-tinted badge deep-linking into an API reference page. Only active when
  the consumer configures ``theme.code_refs.endpoint`` (a reference page and a
  path-prefix → tag map); otherwise ``endpoint:`` anchors are left untouched.

Markdown is rendered to HTML before ``on_page_content`` runs, so the schemes
have become ``<a href="repo:...">`` / ``<a href="endpoint:...">`` anchors — and
crucially, links inside fenced code blocks are *not* anchors, so code refs
survive verbatim inside ``` fences. This mixin rewrites only those two anchor
families; ordinary links are left untouched.

The look is defined by ``shadcn/css/code-refs.css`` (linked from head.html when
``theme.code_refs`` is set). Nothing here hardcodes a repo or product: the blob
base URL derives from ``config.repo_url`` and every endpoint specific is config.

Config (all optional; the presence of the ``code_refs`` mapping enables the
feature — ``code_refs: {}`` is enough for file badges)::

    theme:
      code_refs:
        # Base URL the file badges link into. Defaults to
        # "<repo_url>/blob" (GitHub/Gitea/GitLab layout). Set to override
        # when repo_url isn't a blob-style host.
        repo_blob_url: null
        # Ref used when the build commit SHA can't be resolved from git.
        default_ref: main
        # Endpoint badges — omit this block to leave endpoint: links alone.
        endpoint:
          # Site-root-relative path of the API reference page. The link is
          # resolved relative to the current page, so any nesting works.
          reference_page: rest-api/
          # Path-prefix → resource tag, mirroring how the reference page
          # slugs its tag anchors (Scalar-style: lowercase, non-alphanumerics
          # collapsed to single hyphens). First matching prefix wins; order
          # matters, so author the more-specific prefixes first.
          tags:
            /api/sessions: Sessions
"""

from __future__ import annotations

from html import escape, unescape
import re
import subprocess

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import get_plugin_logger
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page
from mkdocs.utils import get_relative_url

from shadcn.plugins.mixins.base import Mixin

logger = get_plugin_logger("mixins/code_refs")

# GitHub mark octicon (24x24, fill=currentColor) — the standard GitHub logo.
_GITHUB_OCTICON = (
    '<svg class="md-coderef__icon" viewBox="0 0 24 24" width="14" height="14" '
    'aria-hidden="true"><path fill="currentColor" d="M12 0c-6.626 0-12 5.373-12 '
    "12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338."
    "726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745."
    "083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 "
    "3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 "
    "0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 "
    "3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 "
    "2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 "
    "1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102."
    "823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 "
    '0-6.627-5.373-12-12-12z"></path></svg>'
)

_HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")

# Anchors emitted by markdown for the two custom schemes. Attribute order is
# stable in Python-Markdown output (href first), but match defensively: capture
# the whole href and the inner label, regardless of other attributes.
_ANCHOR_RE = re.compile(
    r'<a\s+href="(?P<scheme>repo|endpoint):(?P<target>[^"]*)"(?P<attrs>[^>]*)>'
    r"(?P<label>.*?)</a>",
    re.IGNORECASE | re.DOTALL,
)

# Line fragment: ``#L12`` or ``#L12-L20`` (the trailing ``-L20`` is optional).
_LINE_FRAGMENT_RE = re.compile(r"#L(?P<start>\d+)(?:-L?(?P<end>\d+))?$")

# Markdown renders a backtick link label (``[`file.py`](repo:...)``) to
# ``<code>file.py</code>`` *inside* the anchor. The badge is already monospace,
# so the inner ``<code>`` wrapper (and any other inline markup) must be stripped
# to plain text — otherwise it gets HTML-escaped and shown literally.
_INNER_TAG_RE = re.compile(r"<[^>]+>")


def _plain_label(inner_html: str) -> str:
    """Reduce an anchor's inner HTML to plain text (strip tags, unescape)."""
    return unescape(_INNER_TAG_RE.sub("", inner_html)).strip()


def _slugify_tag(tag: str) -> str:
    """Slugify a resource tag the way Scalar derives anchor ids from tag names.

    Scalar lowercases, replaces runs of non-alphanumerics with a single hyphen,
    and trims hyphens — e.g. ``Projects & Worktrees`` → ``projects-worktrees``.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", tag.lower())
    return slug.strip("-")


def _resolve_sha(default_ref: str) -> str:
    """Resolve the current commit (short 8-char), falling back to a ref."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        sha = out.stdout.strip()
        return sha or default_ref
    except (OSError, subprocess.SubprocessError):
        return default_ref


class CodeRefsMixin(Mixin):
    """Rewrites ``repo:``/``endpoint:`` anchors into code-reference badges.

    Activated only when ``theme.code_refs`` is set. The build commit SHA is
    resolved once in ``on_config`` and cached, so ``on_page_content`` stays a
    pure-ish function of the page HTML.
    """

    code_refs_activated = False
    code_refs_blob_base = ""
    code_refs_sha = "main"
    # Endpoint support (off unless theme.code_refs.endpoint is configured).
    code_refs_endpoint_page = ""
    code_refs_endpoint_tags: list = []

    def on_config(self, config: MkDocsConfig):
        cr = config.theme.get("code_refs")
        self.code_refs_activated = cr is not None
        if not self.code_refs_activated:
            return super().on_config(config)

        cr = cr or {}
        blob = cr.get("repo_blob_url")
        if not blob and config.repo_url:
            blob = config.repo_url.rstrip("/") + "/blob"
        self.code_refs_blob_base = (blob or "").rstrip("/")
        if not self.code_refs_blob_base:
            logger.warning(
                "code_refs is enabled but no repo_blob_url could be derived "
                "(set theme.code_refs.repo_blob_url or config.repo_url); "
                "file badges will link to a relative path."
            )

        self.code_refs_sha = _resolve_sha(cr.get("default_ref") or "main")

        endpoint = cr.get("endpoint") or {}
        self.code_refs_endpoint_page = endpoint.get("reference_page") or ""
        # Preserve author order: a YAML mapping is ordered in py3.7+.
        self.code_refs_endpoint_tags = list(
            (endpoint.get("tags") or {}).items()
        )

        logger.info("Code-refs mixin activated.")
        return super().on_config(config)

    # -- badge builders --------------------------------------------------

    def _file_badge(self, label: str, target: str) -> str:
        """Render a ``repo:`` file reference into a two-cell badge."""
        path = target
        start = end = None
        m = _LINE_FRAGMENT_RE.search(target)
        if m:
            path = target[: m.start()]
            start = m.group("start")
            end = m.group("end") or start

        path = path.strip()
        safe_label = escape(label.strip() or path.rsplit("/", 1)[-1])
        base = f"{self.code_refs_blob_base}/{self.code_refs_sha}".rstrip("/")

        if start is not None:
            end = end or start  # narrow to str; a missing end is a single line
            href = f"{base}/{path}?plain=1#L{start}-L{end}"
            lines_cell = (
                f'<span class="md-coderef__lines">{escape(start)}'
                f"&ndash;{escape(end)}</span>"
                if start != end
                else f'<span class="md-coderef__lines">{escape(start)}</span>'
            )
        else:
            href = f"{base}/{path}"
            lines_cell = ""

        return (
            f'<a href="{escape(href, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer" class="md-coderef md-coderef--file">'
            f'<span class="md-coderef__label">{_GITHUB_OCTICON}{safe_label}'
            f"</span>{lines_cell}</a>"
        )

    def _endpoint_badge(self, label: str, target: str, page_url: str) -> str:
        """Render an ``endpoint:`` reference into a method-tinted badge."""
        method = ""
        path = target.strip()
        parts = target.strip().split(None, 1)
        if parts and parts[0].upper() in _HTTP_METHODS:
            method = parts[0].upper()
            path = parts[1].strip() if len(parts) > 1 else ""

        tag = next(
            (
                t
                for prefix, t in self.code_refs_endpoint_tags
                if path.startswith(prefix)
            ),
            None,
        )
        ref = get_relative_url(self.code_refs_endpoint_page, page_url)
        href = f"{ref}#tag/{_slugify_tag(tag)}" if tag else ref

        # The method already shows in its own tinted cell, so the label is the
        # path alone — strip a leading "METHOD " the author may have repeated in
        # the link text (``[POST /api/sessions]`` → label ``/api/sessions``).
        display = label.strip() or path or target.strip()
        if method:
            head_word, _, tail = display.partition(" ")
            if head_word.upper() == method:
                display = tail.strip() or path
        safe_label = escape(display or path)
        method_mod = f" md-coderef--{method.lower()}" if method else ""
        method_cell = (
            f'<span class="md-coderef__method">{escape(method)}</span>'
            if method
            else ""
        )

        return (
            f'<a href="{escape(href, quote=True)}" '
            f'class="md-coderef md-coderef--endpoint{method_mod}">'
            f"{method_cell}"
            f'<span class="md-coderef__label">{safe_label}</span></a>'
        )

    # -- hook ------------------------------------------------------------

    def on_page_content(
        self,
        html_content: str,
        page: Page,
        config: MkDocsConfig,
        files: Files,
    ) -> str:
        if not self.code_refs_activated:
            return super().on_page_content(html_content, page, config, files)
        if "repo:" not in html_content and "endpoint:" not in html_content:
            return super().on_page_content(html_content, page, config, files)

        endpoint_on = bool(self.code_refs_endpoint_page)
        page_url = page.url if page is not None else ""

        def _replace(match: re.Match) -> str:
            scheme = match.group("scheme").lower()
            target = unescape(match.group("target"))
            label = _plain_label(match.group("label"))
            if scheme == "repo":
                return self._file_badge(label, target)
            if endpoint_on:
                return self._endpoint_badge(label, target, page_url)
            return match.group(0)  # endpoint disabled — leave anchor untouched

        html_content = _ANCHOR_RE.sub(_replace, html_content)
        return super().on_page_content(html_content, page, config, files)
