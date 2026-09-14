"""Build-time icon resolution: batching, caching, and how failures degrade.

These stub the one HTTP call and exercise the real resolution path, because
the behavior worth pinning is *how many requests a build makes and what it
renders when they fail* -- not the shape of the JSON. Every test that asserts
a request count would pass trivially against a lazy implementation returning
the same SVG, so each one checks the count and the markup together.
"""

from __future__ import annotations

import json

import pytest

from shadcn import iconify as mod
from shadcn.iconify import IconCache, theme_icon_names

# One 24x24 square icon and one 256x153 wide icon: the aspect-ratio scaling
# below is invisible on a square, which is why a wide one is in every fixture.
LUCIDE = {
    "prefix": "lucide",
    "width": 24,
    "height": 24,
    "icons": {
        "house": {"body": "<path d='M1 1'/>"},
        "rocket": {"body": "<path d='M2 2'/>"},
    },
}
LOGOS = {
    "prefix": "logos",
    "width": 256,
    "height": 256,
    "icons": {"aws": {"body": "<path d='M3 3'/>", "height": 153}},
}


class FakeApi:
    """Records every URL requested and answers from the fixtures above."""

    def __init__(self, collections=None, fail=False):
        self.collections = collections or {"lucide": LUCIDE, "logos": LOGOS}
        self.calls = []
        self.fail = fail

    def __call__(self, url: str):
        self.calls.append(url)
        if self.fail:
            return None
        prefix = url.split("/")[-1].split(".json")[0].split(".svg")[0]
        source = self.collections.get(prefix)
        if source is None:
            return None
        wanted = url.split("icons=")[-1].split("&")[0].replace("%2C", ",")
        names = [n for n in wanted.split(",") if n]
        payload = {k: v for k, v in source.items() if k != "icons"}
        payload["icons"] = {
            n: source["icons"][n] for n in names if n in source["icons"]
        }
        missing = [n for n in names if n not in source["icons"]]
        if missing:
            payload["not_found"] = missing
        return json.dumps(payload)


@pytest.fixture
def api(monkeypatch):
    fake = FakeApi()
    monkeypatch.setattr(mod, "_fetch", fake)
    return fake


def test_warm_fetches_one_request_per_prefix(api):
    """The whole point: request count scales with icon SETS, not icons.

    A site's ~45 nav icons resolving one-by-one is what got a CI build
    rate-limited into an aborted deploy.
    """
    cache = IconCache(None)
    cache.warm(["lucide:house", "lucide:rocket", "logos:aws", "lucide:house"])

    assert len(api.calls) == 2, api.calls
    lucide_call = next(c for c in api.calls if "lucide" in c)
    assert "house" in lucide_call and "rocket" in lucide_call

    # Warming must actually populate, or it is two wasted requests plus the
    # lazy fetches it was supposed to replace.
    before = len(api.calls)
    assert "<svg" in cache.svg("lucide:house", "16px")
    assert "<svg" in cache.svg("logos:aws", "16px")
    assert len(api.calls) == before


def test_width_scales_by_aspect_ratio_rounding_up(api):
    """The API rounds a scaled width UP to 2dp; `round()` is off by 0.01.

    Measured against the live API: a 256x153 icon at 16px is `26.78px`.
    """
    cache = IconCache(None)
    assert 'width="16px" height="16px"' in cache.svg("lucide:house", "16px")
    assert 'width="26.78px" height="16px"' in cache.svg("logos:aws", "16px")
    assert 'viewBox="0 0 256 153"' in cache.svg("logos:aws", "16px")


def test_throttled_build_renders_a_runtime_fallback(monkeypatch):
    """A failed fetch must leave something the browser can still paint.

    The old filter emitted `<svg></svg>` -- a hole in the page -- and logged
    an error that aborted `--strict`. Throttling is transient and not the
    site's fault, so it degrades instead of failing.
    """
    failing = FakeApi(fail=True)
    monkeypatch.setattr(mod, "_fetch", failing)
    cache = IconCache(None)

    rendered = cache.svg("lucide:house", "16px")
    assert "<iconify-icon" in rendered and 'icon="lucide:house"' in rendered
    assert "<svg></svg>" not in rendered


def test_unknown_icon_is_an_error_not_a_silent_blank(api, caplog):
    """A typo is the site's own bug, so it must stay a hard `--strict` error.

    `lucide:diagram-3` (a Bootstrap name with no lucide twin) broke a real
    deploy; resilience to throttling must not also swallow this.
    """
    cache = IconCache(None)
    with caplog.at_level("ERROR"):
        cache.svg("lucide:diagram-3", "16px")
    assert any("diagram-3" in r.message for r in caplog.records)


def test_disk_cache_makes_a_rebuild_free(tmp_path, monkeypatch):
    fake = FakeApi()
    monkeypatch.setattr(mod, "_fetch", fake)
    warm = IconCache(tmp_path)
    warm.warm(["lucide:house"])
    warm.svg("lucide:house", "16px")
    warm.flush()

    rebuild = IconCache(tmp_path)
    calls_before = len(fake.calls)
    assert "<svg" in rebuild.svg("lucide:house", "16px")
    assert len(fake.calls) == calls_before


def test_malformed_key_is_rejected(api):
    cache = IconCache(None)
    for bad in ("house", "", "a:b:c"):
        with pytest.raises(ValueError):
            cache.svg(bad, "16px")


def test_theme_icon_names_censuses_both_config_surfaces():
    """`nav_icons` and `header_tabs` are the two places a site declares icons.

    Missing either sends those icons back down the one-request-each path the
    batch exists to remove, and nothing fails visibly when that happens.
    """

    class Config:
        theme = {
            "nav_icons": {"Home": "lucide:house"},
            "header_tabs": [{"label": "Guide", "icon": "lucide:book-open"}],
            "icon": "logos/logo.png",
        }

    names = theme_icon_names(Config())
    assert "lucide:house" in names
    assert "lucide:book-open" in names
    # A file path is served from disk; sending it to the API would 404.
    assert not any("logo.png" in n for n in names)
    # The theme's own template icons must ride along in the same batch.
    assert "lucide:menu" in names
