import urllib.parse
import urllib.request
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Union
from urllib.error import URLError

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import get_plugin_logger
from mkdocs.structure.nav import Navigation, Section
from mkdocs.structure.pages import Page

logger = get_plugin_logger("filters")


@lru_cache()
def iconify(key: str, height: str = "20px", **kwargs) -> str:
    base_url = "https://api.iconify.design"
    icon = key.split(":")
    if len(icon) != 2:
        raise ValueError(
            f"Invalid icon format: {key}. Expected format 'provider:name'."
        )
    # collapse icon
    provider, name = icon
    url = f"{base_url}/{provider}/{name}.svg?{urllib.parse.urlencode({'height': height, **kwargs})}"

    # need to provide a user-agent to fix cloudlfare 403 error
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "mkdocs-shadcn"},
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.read().decode(
                "utf-8"
            )  # Convert to string if needed
    except URLError as err:
        logger.error(f"fail to call iconify api: {err} ({url})")

    return "<svg></svg>"


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
