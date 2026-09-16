import subprocess
import urllib.parse
from collections.abc import Mapping
from pathlib import Path
from typing import Any, List, Optional, Union

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import get_plugin_logger
from mkdocs.structure.nav import Navigation, Section
from mkdocs.structure.pages import Page

from shadcn.iconify import IconCache

logger = get_plugin_logger("filters")

#: The build's icon cache. Set by the plugin's `on_config` so resolution is
#: batched and persisted per build; a default instance keeps the filter usable
#: on its own (tests, or a template rendered outside a full build).
_icons = IconCache()


def set_icon_cache(cache: Optional[IconCache]) -> None:
    """Point the `iconify` filter at this build's cache."""
    global _icons
    _icons = cache if cache is not None else IconCache()


def iconify(key: str, height: str = "20px", **kwargs) -> str:
    """Inline SVG for an Iconify `provider:name`, resolved at build time.

    Fetching is batched per provider and cached on disk by `IconCache`,
    because the per-icon endpoint throttles a CI runner hard enough to abort a
    strict build. See `shadcn/iconify.py` for why that matters.
    """
    return _icons.svg(key, height, **kwargs)


def parse_author(site_author: str) -> Union[str, None]:
    """Returns the email address of the site author."""
    # parse thinks like "Alban Siffer <31479857+asiffer@users.noreply.github.com>"
    if "<" in site_author and ">" in site_author:
        chunks = site_author.split("<")
        email = chunks[-1].split(">")[0]
        name = chunks[0].strip()
    else:
        email = None
        name = site_author.strip()

    if email:
        return f'<a href="mailto:{email}">{name}</a>'
    return f"<span>{name}</span>"


def setattribute(value: Union[dict, object], k: str, v: Any):
    if hasattr(value, "__setattr__"):
        setattr(value, k, v)
    return value


def _git_branch(cwd: Optional[Path] = None) -> Optional[str]:
    """Branch name of the repo holding ``cwd``, or ``None`` outside a repo.

    ``cwd`` is load-bearing and not a convenience: the build runs from
    wherever the operator invoked ``mkdocs``, which for a theme developer is
    the THEME's checkout, not the docs site's. Without it this reported the
    theme repo's branch and stamped it into every consumer's URLs.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(cwd) if cwd else None,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    branch = out.stdout.strip()
    # A CI checkout of a tag or a bare SHA reports "HEAD"; that is not a ref a
    # forge URL can be built from, so treat it as unknown.
    return branch if branch and branch != "HEAD" else None


#: mkdocs' own hardcoded `edit_uri` defaults, filled in whenever a site sets
#: `repo_url` and nothing else. They pin the branch to `master`/`default`,
#: which is wrong for most repos — so they are recognised and ignored rather
#: than being mistaken for something the consumer asked for.
_MKDOCS_EDIT_URI_DEFAULTS = frozenset(
    {"edit/master/docs/", "src/default/docs/"}
)


def page_source_url(page: Any, config: Any = None) -> str:
    """Public URL of a page's Markdown source, or ``""`` if it has none.

    Deliberately NOT derived from ``page.edit_url``. When a site sets only
    ``repo_url``, mkdocs fills ``edit_uri`` from a hardcoded
    ``edit/master/docs/`` — so every repo whose published branch is not
    ``master`` gets a URL that 404s. Verified 2026-09-16 against both
    consumers of this theme, neither of which publishes a ``master``.

    The ref is resolved in four steps, most explicit first:

    1. ``theme.source_ref``. The only one that is always right, because the
       published branch is not always discoverable from the checkout: Grove's
       working copy is on ``main`` while its public mirror carries only
       ``current``, so a URL built from the local branch 404s. A site whose
       docs repo differs from its publish target needs to say so.
    2. An ``edit_uri`` the consumer set themselves — mkdocs' native way to
       express this, so it is honoured. mkdocs' own invented defaults are
       recognised and skipped.
    3. The checkout's branch, which is right for the common case where a repo
       is published from the branch you are standing on.
    4. ``main``, not ``master``: the default for new repos on every major
       forge, and the thing mkdocs' default gets wrong.

    Returns ``""`` when the site sets no ``repo_url``, which is what the
    template tests to decide whether the repo-backed menu items exist at all.
    """
    repo_url = _config_get(config, "repo_url")
    src_uri = getattr(getattr(page, "file", None), "src_uri", None)
    if not repo_url or not src_uri:
        return ""

    # GitHub/Gitea serve a file's rendered page under `/blob/` and its raw
    # bytes under `/raw/`. Raw is what both menu items want: "View as
    # Markdown" should show source, and an assistant handed a `/blob/` URL
    # fetches forge chrome and has to dig the content back out of it.
    explicit = _config_get(config, "edit_uri")
    if explicit and explicit not in _MKDOCS_EDIT_URI_DEFAULTS:
        base = urllib.parse.urljoin(
            repo_url.rstrip("/") + "/", explicit.lstrip("/")
        )
        base = base.replace("/edit/", "/raw/", 1).replace("/blob/", "/raw/", 1)
        return base.rstrip("/") + "/" + src_uri

    theme = _config_get(config, "theme")
    ref = _config_get(theme, "source_ref")
    if not ref:
        config_path = _config_get(config, "config_file_path")
        root = Path(config_path).resolve().parent if config_path else None
        ref = _git_branch(root) or "main"
    return f"{repo_url.rstrip('/')}/raw/{ref}/{_docs_prefix(config)}{src_uri}"


def _docs_prefix(config: Any) -> str:
    """``docs_dir`` as a repo-relative path prefix, e.g. ``"docs/"``.

    ``docs_dir`` is absolute by the time mkdocs hands it over, so it is made
    relative to the directory holding ``mkdocs.yml`` — which is the repo root
    for every layout this theme has seen.
    """
    docs_dir = _config_get(config, "docs_dir")
    config_path = _config_get(config, "config_file_path")
    if not docs_dir or not config_path:
        return "docs/"
    try:
        rel = (
            Path(docs_dir)
            .resolve()
            .relative_to(Path(config_path).resolve().parent)
        )
    except (ValueError, OSError):
        return "docs/"
    return "" if str(rel) == "." else f"{rel.as_posix()}/"


def active_section(nav: Navigation) -> Union[Section, None]:
    """Return the top-level active section"""
    for item in nav:
        if isinstance(item, Section) and item.is_section and item.active:
            return item
    return None


def _config_get(cfg: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` from a mapping-like or attribute-bearing config object.

    Handles mkdocs' ``Theme`` (dict-like), plain dicts, and objects. A missing
    key or an explicit ``None`` both collapse to ``default``.
    """
    if cfg is None:
        return default
    try:
        val = cfg[key]
    except (KeyError, TypeError, IndexError):
        val = getattr(cfg, key, default)
    return default if val is None else val


def _claimed_sections(theme: Any) -> List[str]:
    """Top-level Section titles claimed by any ``header_tabs[].section`` entry."""
    tabs = _config_get(theme, "header_tabs")
    if not tabs:
        return []
    claimed = []
    for tab in tabs:
        if not isinstance(tab, Mapping):
            continue
        title = tab.get("section")
        if title:
            claimed.append(str(title))
    return claimed


def scoped_nav(nav: Navigation, theme: Any) -> list:
    """Resolve the top-level nav items the left sidebar should render.

    Fork feature. When ``theme.header_tabs`` is set and at least one tab
    declares ``section: <exact top-level Section title>``, the sidebar is
    scoped per tab:

      - a page inside a claimed Section (matched by exact title) shows ONLY
        that Section's children;
      - every other page (root-tab pages, or pages in unclaimed sections)
        shows the full nav MINUS all claimed Sections.

    When no tab claims a section, the upstream ``topbar_sections`` behavior is
    preserved verbatim (active-section children, else the full nav). Any lookup
    miss or empty result degrades to the full nav — this never raises.
    """
    try:
        claimed = _claimed_sections(theme)
        if claimed:
            for item in nav:
                if (
                    isinstance(item, Section)
                    and item.is_section
                    and item.active
                ):
                    # The active top-level section decides the scope. A claimed
                    # one narrows to its children; an unclaimed one means we are
                    # on a "root" page and fall through to the minus-claimed view.
                    if item.title in claimed:
                        return list(item.children)
                    break
            remaining = [
                item
                for item in nav
                if not (
                    isinstance(item, Section)
                    and item.is_section
                    and item.title in claimed
                )
            ]
            return remaining or list(nav)
        if _config_get(theme, "topbar_sections"):
            section = active_section(nav)
            return list(section.children) if section is not None else []
        return list(nav)
    except Exception as err:  # never break the build over sidebar scoping
        logger.warning(f"scoped_nav fell back to full nav: {err}")
        return list(nav)


def first_page(section: Section) -> Union[Page, None]:
    """Return the first page in a section"""
    for item in section.children:
        if isinstance(item, Page) and item.is_page:
            return item

    for item in section.children:
        if isinstance(item, Section):
            fp = first_page(item)
            if fp:
                return fp

    return None


# config is provided by shadcn/plugins/search.py
def file_exists(path: str, config: MkDocsConfig) -> bool:
    """Check if a file exists at the given path, from docs_dir"""
    p: Path = Path(config.docs_dir) / Path(path)
    return p.exists() and p.is_file()


def is_http_url(path: str) -> bool:
    """Check if a path is a valid URL (http, https and also data scheme)"""
    try:
        parsed = urllib.parse.urlparse(path)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https", "data"):
        return False
    return True


def read_file(path: str, config: MkDocsConfig) -> str:
    """Read raw text content from a file, resolved from docs_dir"""
    p: Path = Path(config.docs_dir) / path
    try:
        return p.read_text(encoding="utf-8")
    except OSError as err:
        logger.error(f"failed to read file: {err} ({p})")
        return ""


def is_svg(path: str) -> bool:
    """Check if a path points to an SVG file, based on extension"""
    return Path(path).suffix.lower() == ".svg"
