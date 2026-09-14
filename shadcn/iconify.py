"""Resolve Iconify icon names to inline SVG at build time.

Every icon on a page is fetched while the site builds, so a docs build is only
as reliable as `api.iconify.design` is willing to be. It is not very willing:
the per-icon `/{prefix}/{name}.svg` endpoint throttles hard from a shared
egress IP, which is exactly what a CI runner has. A consumer site with ~45 nav
icons made ~50 sequential requests per build and got `429 Too Many Requests`
for most of them; under `--strict` each one is an error, so a whole docs deploy
aborted on a dependency that was merely rate-limiting, not down.

Two independent measures fix that, in this order:

**Batch.** `/{prefix}.json?icons=a,b,c` returns every icon of one prefix in a
single response, so a build costs one request per *prefix* (two, in practice:
`lucide` and `simple-icons`) instead of one per icon per size. That is the real
cure, and it was measured to be the difference between throttled and not: with
the per-icon endpoint returning 429, the JSON endpoint answered 200 from the
same address in the same second. They are metered separately.

**Cache.** Resolved icons are memoized per prefix for the life of the build,
and persisted under the site's cache directory so a rebuild (and any CI run
that restores that directory) costs nothing at all.

The SVG this module assembles is byte-identical to what the `.svg` endpoint
returns -- verified over 22 icon/size pairs spanning `lucide`, `simple-icons`
and `logos`, square and non-square. `_scaled_width` is the fiddly half: the API
scales width by the icon's aspect ratio and rounds it UP to two decimals
(`256x153` at `16px` is `26.78px`, not `26.77`), so this uses `ceil` rather
than `round`. Getting that wrong is invisible on a square icon, which is most
of them, and misaligns every logo.

A name that genuinely does not exist is still an error, because that is a typo
in the consumer's config and silence would ship a blank square. Throttling and
outages are warnings instead: the page still renders, and the theme's runtime
`iconify-icon` script paints the icon in the browser.
"""

from __future__ import annotations

import json
import math
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError

from mkdocs.plugins import get_plugin_logger

logger = get_plugin_logger("iconify")

API_BASE = "https://api.iconify.design"

#: Cloudflare answers 403 to a request with no user-agent.
USER_AGENT = "mkdocs-shadcn"

#: A 429 is the API asking for a pause, so honour it rather than hammering.
#: Short by design: the batch endpoint makes ~2 requests per build, so this
#: is a safety net for an unlucky build, not the mechanism keeping us inside
#: the budget. A build must not hang for minutes on a flaky dependency.
_RETRIES = 3
_BACKOFF_SECONDS = 2.0
_TIMEOUT_SECONDS = 15.0

#: `20px` -> `(20.0, "px")`; a bare `20` or `1em` works the same way.
_DIMENSION = re.compile(r"\s*([0-9]*\.?[0-9]+)\s*([a-z%]*)\s*\Z", re.I)


def _fetch(url: str) -> Optional[str]:
    """GET `url`, retrying a 429 with linear backoff. None on failure."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(_RETRIES):
        try:
            with urllib.request.urlopen(
                request, timeout=_TIMEOUT_SECONDS
            ) as response:
                return response.read().decode("utf-8")
        except HTTPError as err:
            retriable = err.code == 429 or 500 <= err.code < 600
            if not retriable or attempt == _RETRIES - 1:
                logger.warning(f"iconify api: {err} ({url})")
                return None
            time.sleep(_BACKOFF_SECONDS * (attempt + 1))
        except (URLError, OSError, TimeoutError) as err:
            logger.warning(f"iconify api: {err} ({url})")
            return None
    return None


def _format_dimension(value: float) -> str:
    """Two decimals at most, trailing zeros trimmed -- the API's own format."""
    return f"{math.ceil(value * 100) / 100:.2f}".rstrip("0").rstrip(".") or "0"


def _scaled_width(height: str, width: float, box_height: float) -> str:
    """Width that preserves the icon's aspect ratio at `height`.

    The API returns `width="26.78px"` for a 256x153 icon asked for at 16px. A
    height carrying no parseable number (a CSS keyword, say) is handed back
    unchanged, which is what the API does too.
    """
    parsed = _DIMENSION.match(height)
    if parsed is None or not box_height:
        return height
    magnitude, unit = float(parsed.group(1)), parsed.group(2)
    return f"{_format_dimension(magnitude * width / box_height)}{unit}"


class IconCache:
    """Build-time icon resolution, batched per prefix and cached on disk.

    One instance per build. Prefixes are fetched whole on first use and reused
    for every later icon of that prefix, so the request count scales with the
    number of icon *sets* a site uses rather than the number of icons.
    """

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        self._collections: Dict[str, dict] = {}
        self._rendered: Dict[Tuple[str, str, str], str] = {}
        self._cache_dir = cache_dir
        self._dirty = False

    # -- disk -------------------------------------------------------------

    def _cache_file(self, prefix: str) -> Optional[Path]:
        if self._cache_dir is None:
            return None
        return self._cache_dir / f"{prefix}.json"

    def _load_from_disk(self, prefix: str) -> Optional[dict]:
        path = self._cache_file(prefix)
        if path is None or not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as err:
            logger.debug(f"unreadable icon cache, refetching: {err} ({path})")
            return None

    def flush(self) -> None:
        """Persist fetched collections. Best effort: a build must not fail here."""
        path_dir = self._cache_dir
        if path_dir is None or not self._dirty:
            return
        try:
            path_dir.mkdir(parents=True, exist_ok=True)
            for prefix, collection in self._collections.items():
                cache_file = self._cache_file(prefix)
                if cache_file is not None:
                    cache_file.write_text(
                        json.dumps(collection), encoding="utf-8"
                    )
        except OSError as err:
            logger.debug(f"could not write icon cache: {err}")
        self._dirty = False

    # -- network ----------------------------------------------------------

    def _local(self, prefix: str) -> dict:
        """The in-memory collection for `prefix`, seeded from disk once."""
        collection = self._collections.get(prefix)
        if collection is None:
            collection = self._load_from_disk(prefix) or {"icons": {}}
            self._collections[prefix] = collection
        return collection

    def _known(self, collection: dict, name: str) -> bool:
        return name in collection.get("icons", {}) or name in collection.get(
            "_missing", []
        )

    def warm(self, keys: Iterable[str]) -> None:
        """Resolve `keys` up front, one request per icon set.

        This is what keeps a build off the rate limiter: without it each icon
        is fetched on first render and a site with 45 nav icons makes 45
        requests, which is the shape that got throttled. Grouping by prefix
        turns that into one request per set -- two, for a site using `lucide`
        and `simple-icons`.
        """
        wanted: Dict[str, set] = {}
        for key in keys:
            prefix, _, name = str(key).partition(":")
            if not prefix or not name or ":" in name:
                continue
            if not self._known(self._local(prefix), name):
                wanted.setdefault(prefix, set()).add(name)
        for prefix, names in wanted.items():
            self._fetch_names(prefix, sorted(names))

    def _fetch_names(self, prefix: str, names: List[str]) -> Optional[dict]:
        """Fetch `names` of one prefix in a single request and merge them in."""
        collection = self._local(prefix)
        query = urllib.parse.urlencode({"icons": ",".join(names)})
        payload = _fetch(f"{API_BASE}/{prefix}.json?{query}")
        if payload is None:
            return None
        try:
            fetched = json.loads(payload)
        except ValueError as err:
            logger.warning(f"iconify api returned invalid JSON: {err}")
            return None

        # Collection-level geometry is shared by every icon in the set, so the
        # merge has to carry it across, not just the icon bodies.
        for key, value in fetched.items():
            if key == "icons":
                collection.setdefault("icons", {}).update(value)
            elif key == "not_found":
                collection.setdefault("_missing", []).extend(value)
            else:
                collection[key] = value
        self._dirty = True
        return collection

    def _collection(self, prefix: str, name: str) -> Optional[dict]:
        """The collection holding `name`, fetching it if `warm` did not."""
        collection = self._local(prefix)
        if self._known(collection, name):
            return collection
        return self._fetch_names(prefix, [name])

    # -- rendering --------------------------------------------------------

    def svg(self, key: str, height: str = "20px", **kwargs: str) -> str:
        """Inline `<svg>` for `key` (`"prefix:name"`), sized to `height`.

        Falls back to an `<iconify-icon>` element the browser resolves at
        runtime, so a throttled build still ships a page with its icons.
        """
        prefix, _, name = key.partition(":")
        if not prefix or not name or ":" in name:
            raise ValueError(
                f"Invalid icon format: {key}. Expected format 'provider:name'."
            )

        memo_key = (key, height, json.dumps(kwargs, sort_keys=True))
        cached = self._rendered.get(memo_key)
        if cached is not None:
            return cached

        # `color` and friends are rare enough that the per-icon endpoint stays
        # the honest answer for them: it applies the transform server-side, and
        # reimplementing that here would be a second renderer to keep correct.
        if kwargs:
            rendered = self._svg_via_api(prefix, name, height, kwargs)
        else:
            rendered = self._svg_from_collection(prefix, name, height)

        if rendered is None:
            rendered = _runtime_fallback(key, height)
        self._rendered[memo_key] = rendered
        return rendered

    def _svg_from_collection(
        self, prefix: str, name: str, height: str
    ) -> Optional[str]:
        collection = self._collection(prefix, name)
        if collection is None:
            return None
        icon = collection.get("icons", {}).get(name)
        if icon is None:
            # The API positively reported the name as absent, which is a typo
            # in the site's own config -- a class of failure a warning would
            # bury and that no amount of retrying will fix.
            logger.error(
                f"unknown icon: {prefix}:{name} is not in the {prefix} set"
            )
            return None

        box_width = float(icon.get("width", collection.get("width", 16)))
        box_height = float(icon.get("height", collection.get("height", 16)))
        left = icon.get("left", collection.get("left", 0))
        top = icon.get("top", collection.get("top", 0))
        width = _scaled_width(height, box_width, box_height)
        box = f"{left} {top} {_number(box_width)} {_number(box_height)}"
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" height="{height}" viewBox="{box}">'
            f"{icon['body']}</svg>"
        )

    def _svg_via_api(
        self, prefix: str, name: str, height: str, params: Dict[str, str]
    ) -> Optional[str]:
        query = urllib.parse.urlencode({"height": height, **params})
        return _fetch(f"{API_BASE}/{prefix}/{name}.svg?{query}")


#: Icons the theme's own templates name directly. A template is rendered per
#: page, so leaving these to lazy resolution would put them in the first page's
#: request burst -- exactly what the warm pass exists to avoid. Kept beside the
#: templates that use them; a name added to a template belongs here too.
THEME_ICONS = (
    "lucide:chevron-right",
    "lucide:list",
    "lucide:menu",
    "lucide:moon",
    "lucide:search",
    "lucide:send",
    "lucide:sparkles",
    "lucide:sun",
    "lucide:x",
    "simple-icons:github",
)


def theme_icon_names(config) -> List[str]:
    """Every icon name this site will render, for a single batched prefetch.

    Covers the theme's own template icons plus the two places a consumer
    declares them (`nav_icons`, `header_tabs`) and `theme.icon` when it names
    an Iconify icon rather than a file. Content-authored `<iconify-icon>` tags
    resolve in the browser and never reach this module.
    """
    names: List[str] = list(THEME_ICONS)
    theme = getattr(config, "theme", None)

    def read(key):
        if theme is None:
            return None
        try:
            return theme[key]
        except (KeyError, TypeError):
            return getattr(theme, key, None)

    nav_icons = read("nav_icons")
    if isinstance(nav_icons, dict):
        names.extend(str(v) for v in nav_icons.values() if v)

    tabs = read("header_tabs")
    if isinstance(tabs, (list, tuple)):
        for tab in tabs:
            icon = tab.get("icon") if hasattr(tab, "get") else None
            if icon:
                names.append(str(icon))

    icon = read("icon")
    # A file path or URL is handled by `icon.html` without touching the API.
    if isinstance(icon, str) and ":" in icon and "/" not in icon:
        names.append(icon)

    return names


def _number(value: float) -> str:
    """Render a float without a pointless `.0`, matching the API's viewBox."""
    return str(int(value)) if float(value).is_integer() else str(value)


def _runtime_fallback(key: str, height: str) -> str:
    """Let the browser fetch what the build could not.

    `main.html` always loads the `iconify-icon` web component, so this element
    resolves client-side. It means a throttled build degrades to a slightly
    later icon paint rather than to a hole in the page.
    """
    return (
        f'<iconify-icon icon="{key}" height="{height}" '
        'aria-hidden="true"></iconify-icon>'
    )
