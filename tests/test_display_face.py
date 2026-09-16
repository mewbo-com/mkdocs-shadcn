"""Headings wear the serif display face; everything around them does not.

The treatment sets H1-H3, card titles and brand lettering in IBM Plex Serif
against a Geist body. What is worth pinning is not that the serif is applied —
a glance catches that — but the BOUNDARY, because every failure mode here is
silent. A selector that broadens by one level puts a serif on running text, a
selector that narrows drops the face entirely, and in both cases the build
succeeds and the page merely reads wrong.

Four boundaries, each of which has a reason to be exactly where it is:

  H3 is the floor       Below it, headings run close to body size, where a
                        serif stops reading as deliberate.
  code keeps the mono   A code span in a heading names a symbol. The two rules
                        collide at equal specificity, so this is decided by an
                        explicit rule rather than by source order.
  .doc and .ms-hero     mkdocstrings headings ARE symbols, and the hero is
                        brand composition with its own type treatment.
  --font-display        The token is deliberately not --font-serif (Tailwind
                        v4 owns that for its `font-serif` utility) and
                        deliberately not a repoint of --font-sans (mermaid
                        canvas-measures diagram labels with it).
"""

import pytest
from playwright.sync_api import Page

SERIF = "IBM Plex Serif"
SANS = "Geist"
MONO = "Geist Mono"

# Resolved first family, so an assertion reads as the face a reader sees
# rather than as the whole fallback stack.
FIRST_FAMILY = """
  async (sel) => {
    await document.fonts.ready;
    const el = document.querySelector(sel);
    if (!el) return null;
    return getComputedStyle(el).fontFamily.split(',')[0].replace(/["']/g, '').trim();
  }
"""


def first_family(page: Page, selector: str) -> str | None:
    return page.evaluate(FIRST_FAMILY, selector)


@pytest.fixture
def fixture_page(page: Page, local_deployment: str) -> Page:
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(
        local_deployment + "/display_face_regression/",
        wait_until="networkidle",
    )
    return page


@pytest.mark.parametrize(
    "label,selector",
    [
        ("page title", "article #page-header h1"),
        ("prose H2", "article .typography h2"),
        ("prose H3", "article .typography h3"),
        ("card title", ".ms-card__title"),
    ],
)
def test_headings_wear_the_display_face(
    fixture_page: Page, label: str, selector: str
):
    family = first_family(fixture_page, selector)
    assert family is not None, f"no {label} on the fixture page"
    assert family == SERIF, (
        f"{label} resolves to {family!r}, not the display face — the heading "
        f"rule in mewbo.css no longer reaches it, or base.css now wins on "
        f"source order"
    )


@pytest.mark.parametrize(
    "label,selector",
    [
        # H3 is the floor. These two are where a broadened `:is(h1, h2, h3)`
        # would show up first.
        ("prose H4", "article .typography h4"),
        ("prose H5", "article .typography h5"),
        ("body copy", "article .typography p"),
        ("card body", ".ms-card__body"),
        # Navigation furniture stays on the sans in both rails.
        ("sidebar link", '[data-sidebar="content"] a'),
        ("ToC link", ".mewbo-toc__link"),
    ],
)
def test_prose_and_chrome_stay_on_the_sans(
    fixture_page: Page, label: str, selector: str
):
    family = first_family(fixture_page, selector)
    assert family is not None, f"no {label} on the fixture page"
    assert family == SANS, (
        f"{label} resolves to {family!r} — the display face has spread past "
        f"headings onto text that is read rather than scanned"
    )


def test_code_in_a_heading_keeps_the_mono_face(fixture_page: Page):
    """A code span in a heading names a symbol, so it stays on the mono face.

    This holds without a rule of its own: `article code:not(pre code)` in
    tailwind/article.css reaches (0,2,2) — the `:not(pre code)` is what buys
    the extra class-level — while the heading rule reaches (0,1,2), so the
    code rule wins on specificity no matter the source order. An explicit
    `article :is(h1, h2, h3) code { font-family: var(--font-mono) }` was
    written here first and removed once a mutation test showed the behaviour
    was identical with it gone; do not reintroduce it.

    What this test guards is the OUTCOME, which is still easy to lose — a
    future heading rule that reaches (0,2,2) or higher, or one carrying
    `!important`, would take the code span with it.
    """
    family = first_family(fixture_page, "article .typography h2 code")
    assert family is not None, "no code span inside a heading on the fixture"
    assert family == MONO, (
        f"code inside a heading resolves to {family!r}, not the mono face — "
        f"the heading rule is overriding the inline-code rule again"
    )


def test_hero_headings_opt_out(fixture_page: Page):
    """The hero is brand composition with its own type treatment, excluded by
    name. Being an `:not()` exclusion, this breaks silently if the selector
    is ever rewritten."""
    family = first_family(fixture_page, ".ms-hero h1")
    assert family is not None, "no hero heading on the fixture page"
    assert family == SANS, (
        f"the hero heading resolves to {family!r} — the hero's exclusion from "
        f"the display-face rule has been lost"
    )


def test_mkdocstrings_symbols_opt_out(page: Page, local_deployment: str):
    """An mkdocstrings heading is an API symbol, not a section title. A serif
    `Router.get(path)` is a symbol dressed as prose, and these headings
    legitimately contain code spans."""
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(
        local_deployment + "/plugins/mkdocstrings/", wait_until="networkidle"
    )
    family = first_family(page, ".doc h3")
    assert family is not None, "no mkdocstrings symbol heading on that page"
    assert family == SANS, (
        f"an mkdocstrings symbol heading resolves to {family!r} — the `.doc` "
        f"exclusion has been lost"
    )


def test_brand_lettering_wears_the_display_face(fixture_page: Page):
    """The site name is a wordmark in both header and footer, so both take the
    face for one identity. The small bordered "Docs" badge beside the header
    name is NOT part of the wordmark and is illegible in a serif at 0.525rem."""
    for label, selector in (
        ("header brand name", ".mewbo-brand__name"),
        ("footer brand name", ".mewbo-footer__name"),
    ):
        family = first_family(fixture_page, selector)
        assert family is not None, f"no {label} in the fixture page chrome"
        assert family == SERIF, (
            f"{label} resolves to {family!r}, not the display face"
        )

    badge = first_family(fixture_page, ".mewbo-brand__docs")
    assert badge == SANS, (
        f"the Docs badge resolves to {badge!r} — at 0.525rem a serif is "
        f"illegible, and the badge is a status chip, not part of the wordmark"
    )


def test_header_tab_labels_wear_the_display_face(fixture_page: Page):
    """Header tabs name top-level sections — the same nouns that head the
    pages they lead to."""
    family = first_family(fixture_page, ".ms-header-tabs__item")
    assert family is not None, "no header tabs on the fixture page"
    assert family == SERIF, (
        f"a header tab label resolves to {family!r}, not the display face"
    )


def test_display_face_does_not_hijack_tailwinds_font_serif(fixture_page: Page):
    """Tailwind v4 defines --font-serif in `@layer theme` and its `font-serif`
    utility resolves through it. An override in `@layer base` BEATS `@layer
    theme`, so naming the theme's token --font-serif would repoint that utility
    for every consumer — `class="font-serif"` would stop meaning "a serif" and
    start meaning "the theme's display face". The token is --font-display
    precisely to avoid that, and this pins the two apart."""
    tokens = fixture_page.evaluate(
        """() => {
          const s = getComputedStyle(document.documentElement);
          return {
            display: s.getPropertyValue('--font-display').trim(),
            serif: s.getPropertyValue('--font-serif').trim(),
            sans: s.getPropertyValue('--font-sans').trim(),
          };
        }"""
    )

    assert SERIF in tokens["display"], (
        f"--font-display is {tokens['display']!r} — the display face token no "
        f"longer resolves to the serif"
    )
    assert SERIF not in tokens["serif"], (
        f"--font-serif is {tokens['serif']!r} — the theme has taken over "
        f"Tailwind's own serif token, changing what `font-serif` means for "
        f"every consumer"
    )
    # mermaid measures diagram label text on a Canvas 2D context using
    # --font-sans (tokenFont() in mermaid-init-v2.js). Widening it re-lays-out
    # every diagram on the site.
    assert SERIF not in tokens["sans"], (
        f"--font-sans is {tokens['sans']!r} — the serif has been pushed into "
        f"the body token, which silently re-lays-out every mermaid diagram"
    )


def test_display_face_is_self_hosted(fixture_page: Page):
    """The theme serves every font itself, so a consumer's docs site has no
    third-party font dependency and keeps working offline. A re-sync that
    reintroduces the Google Fonts <link> is a regression."""
    hosts = fixture_page.evaluate(
        """() => [...document.querySelectorAll('link[href], script[src]')]
             .map(el => el.getAttribute('href') || el.getAttribute('src'))
             .filter(u => /fonts\\.(googleapis|gstatic)\\.com/.test(u))"""
    )
    assert hosts == [], (
        f"the page references Google Fonts ({hosts}) — the display face is "
        f"vendored under shadcn/fonts/ and must not be fetched at runtime"
    )

    loaded = fixture_page.evaluate(
        """async () => {
          await document.fonts.ready;
          return [...document.fonts]
            .filter(f => f.family.includes('IBM Plex Serif'))
            .some(f => f.status === 'loaded');
        }"""
    )
    assert loaded, (
        "no IBM Plex Serif face reached 'loaded' — the @font-face src in "
        "plex-serif.css does not resolve to a shipped file"
    )
