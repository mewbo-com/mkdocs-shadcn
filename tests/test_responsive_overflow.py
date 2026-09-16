"""The page itself must never scroll sideways.

Content wider than the column is normal and fine — a code block, a wide
table, an equation. What is not fine is that width reaching the VIEWPORT, so
the reader drags the whole document left and right to read a paragraph. Each
such construct owes the layout its own escape: wrap, or scroll inside its own
box.

These pages are the ones that actually broke, each for a different reason, so
each is named rather than folded into a single crawl:

    code_refs/                a pill with `nowrap` and no `max-width`
    plugins/mkdocstrings/     a flex item keeping `min-width: auto`
    extensions/codexec/       `flex-wrap` on a column sizing to its widest kid
    extensions/hover_card/    an anchored tooltip wider than a phone
    plugins/autonumber/       KaTeX display math, which cannot wrap by design

`internal/overflow_probe.py` is the companion diagnostic: it names the
offending element and the ancestors that failed to contain it, which is what
you want while fixing one of these. This file is the gate that keeps it fixed.
"""

import pytest
from playwright.sync_api import Page

# 320 is the narrowest phone still in use; 414 is a large one, where a
# viewport-proportional bug hides but an intrinsic-width one does not.
WIDTHS = (320, 360, 414)

PAGES = (
    "",
    "get_started/",
    "code_refs/",
    "extensions/codexec/",
    "extensions/hover_card/",
    "plugins/autonumber/",
    "plugins/mkdocstrings/",
    "mermaid/",
    "mewbo_components/",
    "table_wrap_regression/",
)


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("path", PAGES)
def test_page_does_not_scroll_horizontally(
    page: Page, local_deployment: str, path: str, width: int
):
    """No page may be wider than the viewport it is shown in."""
    page.set_viewport_size({"width": width, "height": 844})
    page.goto(f"{local_deployment}/{path}", wait_until="networkidle")

    measured = page.evaluate("""() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
    })""")

    # One pixel of slack: sub-pixel layout rounding is not a horizontal
    # scrollbar, and asserting exact equality makes this flaky for no gain.
    assert measured["scrollWidth"] <= measured["clientWidth"] + 1, (
        f"/{path} at {width}px scrolls horizontally: "
        f"{measured['scrollWidth']} > {measured['clientWidth']}"
    )


@pytest.mark.parametrize("width", WIDTHS)
def test_wide_constructs_scroll_themselves_not_the_page(
    page: Page, local_deployment: str, width: int
):
    """Anything too wide to wrap must own a scroll port.

    The failure this guards is a fix that "works" by clipping: an element
    whose content is wider than its box and which neither scrolls nor lives
    inside something that does has silently cut its own content off.
    """
    page.set_viewport_size({"width": width, "height": 844})
    page.goto(f"{local_deployment}/get_started/", wait_until="networkidle")

    clipped = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll(
            'article pre, article .katex-display, article .table-wrapper'
        ).forEach((el) => {
            if (el.scrollWidth <= el.clientWidth + 1) return;
            let node = el;
            let scrolls = false;
            while (node && node.tagName !== 'BODY') {
                const ox = getComputedStyle(node).overflowX;
                if (ox === 'auto' || ox === 'scroll') { scrolls = true; break; }
                node = node.parentElement;
            }
            if (!scrolls) out.push(el.tagName + '.' + el.className);
        });
        return out;
    }""")

    assert clipped == [], f"content clipped with no way to reach it: {clipped}"


def test_signature_headings_wrap_rather_than_widen_the_page(
    page: Page, local_deployment: str
):
    """An mkdocstrings signature is a flex item that must be allowed to shrink.

    Guards the specific regression: `min-width: auto` on the `<code>` inside
    a `display: flex` heading, which refuses to go below its content width and
    drags the document with it.
    """
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(
        f"{local_deployment}/plugins/mkdocstrings/", wait_until="networkidle"
    )

    worst = page.evaluate("""() => {
        let worst = 0;
        document.querySelectorAll('.doc.doc-object h1 > code, ' +
            '.doc.doc-object h2 > code, .doc.doc-object h3 > code, ' +
            '.doc.doc-object h4 > code').forEach((code) => {
            const parent = code.parentElement.getBoundingClientRect().width;
            const overflow = code.getBoundingClientRect().width - parent;
            if (overflow > worst) worst = overflow;
        });
        return worst;
    }""")

    assert worst <= 1, f"signature overflows its heading by {worst}px"


def test_code_reference_pill_is_capped_by_its_column(
    page: Page, local_deployment: str
):
    """A `repo:` badge truncates instead of widening the page."""
    page.set_viewport_size({"width": 320, "height": 844})
    page.goto(f"{local_deployment}/code_refs/", wait_until="networkidle")

    overflowing = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('.md-coderef').forEach((pill) => {
            const own = pill.getBoundingClientRect().width;
            const parent = pill.parentElement.getBoundingClientRect().width;
            if (own > parent + 1) out.push({own, parent});
        });
        return out;
    }""")

    assert overflowing == [], (
        f"pills wider than their container: {overflowing}"
    )


@pytest.mark.parametrize("width", (320, 414))
def test_hover_cards_stay_on_screen_on_phones(
    page: Page, local_deployment: str, width: int
):
    """The anchored tooltip becomes a bottom sheet rather than overflowing.

    Checks both edges: an early version of this fix stopped the page scrolling
    by pushing the card off the LEFT of the viewport instead, which is not a
    fix.
    """
    page.set_viewport_size({"width": width, "height": 844})
    page.goto(
        f"{local_deployment}/extensions/hover_card/", wait_until="networkidle"
    )

    offscreen = page.evaluate("""() => {
        const limit = document.documentElement.clientWidth;
        const out = [];
        document.querySelectorAll('.hover-card').forEach((card) => {
            const box = card.getBoundingClientRect();
            if (box.right > limit + 1 || box.left < -1) {
                out.push({left: Math.round(box.left),
                          right: Math.round(box.right)});
            }
        });
        return out;
    }""")

    assert offscreen == [], f"hover cards off screen at {width}px: {offscreen}"
