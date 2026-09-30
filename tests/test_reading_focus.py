"""The prose column outranks the chrome around it.

Four things pulled the eye off the centre column, each measured on a real
consumer page before it was fixed:

* the left sidebar and right ToC ran 15px entries in full ink, one step from
  the 18px body, with their two section labels at 13.6px/700 and 12.8px/500;
* hovering a sidebar row painted a solid accent block;
* content-tab labels were the only sans-serif headings on a serif page;
* code inside a callout was transparent, so it took on the callout's tint,
  and its border made chips on consecutive lines overlap.

Assertions are comparative where the design is a relationship (rail smaller
than body) and exact only where the value IS the contract (one face per role).
"""

import pytest
from playwright.sync_api import Page

FIXTURE = "/reading_focus_regression/"


@pytest.fixture
def fixture_page(page: Page, local_deployment: str) -> Page:
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(local_deployment + FIXTURE, wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    return page


def _style(page: Page, selector: str) -> dict:
    return page.locator(selector).first.evaluate(
        """el => { const s = getComputedStyle(el); return {
          family: s.fontFamily.split(',')[0].replace(/["']/g, '').trim(),
          size: parseFloat(s.fontSize), weight: s.fontWeight,
          color: s.color, bg: s.backgroundColor }; }"""
    )


def test_rails_sit_a_clear_step_below_the_body(fixture_page: Page):
    body = _style(fixture_page, "article .typography > p")
    entries = [
        _style(fixture_page, 'a[data-sidebar="menu-button"]'),
        _style(fixture_page, ".mewbo-toc__link"),
    ]
    for entry in entries:
        # A clear drop, not one step: at 15/18 the rails competed with prose,
        # and 14/18 was checked on the live sites and still did not recede.
        assert entry["size"] <= body["size"] * 0.75, (entry, body)
    # Both rails use the same entry size.
    assert entries[0]["size"] == entries[1]["size"], entries


def test_sidebar_rows_share_one_tight_pitch(fixture_page: Page):
    """Rows are sized by their text, not by stacked padding and floors.

    A row was 35px around 20px of text (6.4px padding each side over a 32px
    minimum height, plus a 3.2px gap), and a collapsed section kept a 4px
    band under it, so the list spaced unevenly. Half that padding, and every
    row the same height whether it is a page or a section trigger.
    """
    rows = fixture_page.evaluate(
        """() => [...document.querySelectorAll(
            '[data-slot="sidebar"] [data-sidebar="menu"] > li')]
          .filter(li => li.offsetParent)
          .map(li => {
            const b = li.firstElementChild, s = getComputedStyle(b);
            return {h: li.getBoundingClientRect().height,
                    text: parseFloat(s.lineHeight),
                    pad: parseFloat(s.paddingTop) + parseFloat(s.paddingBottom),
                    open: b.getAttribute('data-state') === 'open'};
          })"""
    )
    assert len(rows) >= 3, rows
    for row in rows:
        assert row["pad"] <= row["text"] * 0.4, row
    # An OPEN section's item spans its children, so only single rows compare.
    heights = [r["h"] for r in rows if not r["open"]]
    assert max(heights) - min(heights) <= 1, rows


@pytest.mark.parametrize(
    "selector,ceiling",
    [
        # Each was darkened ~30% from #141414 / #1b1b1b / #202020 / #1f1f1f.
        ("body", 0x10),
        (".mewbo-header", 0x15),
        (".ms-header-tabs", 0x15),
        ("--sidebar", 0x18),
        ("--card", 0x18),
        ("--popover", 0x1A),
    ],
)
def test_dark_surfaces_are_deep(
    fixture_page: Page, selector: str, ceiling: int
):
    fixture_page.evaluate("document.documentElement.classList.add('dark')")
    level = fixture_page.evaluate(
        """sel => {
          const cv = document.createElement('canvas');
          cv.width = cv.height = 1;
          const ctx = cv.getContext('2d', {willReadFrequently: true});
          const root = getComputedStyle(document.documentElement);
          ctx.fillStyle = sel.startsWith('--')
            ? root.getPropertyValue(sel).trim()
            : getComputedStyle(document.querySelector(sel)).backgroundColor;
          ctx.fillRect(0, 0, 1, 1);
          return Math.max(...ctx.getImageData(0, 0, 1, 1).data.slice(0, 3));
        }""",
        selector,
    )
    assert level <= ceiling, f"{selector} is {level:#04x}, over {ceiling:#04x}"


def test_both_rails_label_themselves_identically(fixture_page: Page):
    group = _style(fixture_page, ".mewbo-sidebar-group-label")
    toc = _style(fixture_page, ".mewbo-toc__heading")
    assert (group["family"], group["size"], group["weight"]) == (
        toc["family"],
        toc["size"],
        toc["weight"],
    ), (group, toc)
    entry = _style(fixture_page, 'a[data-sidebar="menu-button"]')
    assert group["size"] <= entry["size"], (group, entry)


@pytest.mark.parametrize("dark", [False, True])
def test_sidebar_hover_is_a_wash_not_a_block(fixture_page: Page, dark: bool):
    if dark:
        fixture_page.evaluate("document.documentElement.classList.add('dark')")
    row = fixture_page.locator(
        '[data-slot="sidebar"] a[data-sidebar="menu-button"]'
        ':not([data-active="true"]):visible'
    ).first
    idle = row.evaluate("el => getComputedStyle(el).color")
    row.hover()
    fixture_page.wait_for_timeout(300)
    # Composite the hover fill over the rail's own stock and measure how far
    # it moves the pixel. The old solid accent block moved it ~40 levels.
    shift = row.evaluate(
        """el => {
          const cv = document.createElement('canvas');
          cv.width = cv.height = 1;
          const ctx = cv.getContext('2d', {willReadFrequently: true});
          const stock = getComputedStyle(document.documentElement)
            .getPropertyValue('--sidebar');
          const px = (...fills) => {
            for (const f of fills) { ctx.fillStyle = f; ctx.fillRect(0, 0, 1, 1); }
            return [...ctx.getImageData(0, 0, 1, 1).data.slice(0, 3)];
          };
          const a = px(stock), b = px(stock, getComputedStyle(el).backgroundColor);
          return a.reduce((s, v, i) => s + Math.abs(v - b[i]), 0);
        }"""
    )
    hovered = row.evaluate("el => getComputedStyle(el).color")
    assert shift <= 36, f"sidebar hover moves the rail by {shift} levels"
    assert hovered != idle, "hover should lift the row's ink instead"


def test_mobile_navigation_keeps_a_reading_size(
    page: Page, local_deployment: str
):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(local_deployment + FIXTURE, wait_until="networkidle")
    page.locator("#menu-button").click()
    size = page.locator(
        'dialog.ms-mobile-nav [data-sidebar="menu-button"]'
    ).first.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
    assert size >= 15, size


def test_tab_labels_wear_the_display_face(fixture_page: Page):
    label = _style(fixture_page, ".tabbed-labels > label")
    heading = _style(fixture_page, "article .typography h2")
    header_tab = _style(fixture_page, ".ms-header-tabs__item")
    assert label["family"] == heading["family"] == header_tab["family"], (
        label,
        heading,
        header_tab,
    )
    # Instrument Serif ships at 400 only; anything heavier is synthesised.
    assert label["weight"] == "400", label


@pytest.mark.parametrize("dark", [False, True])
def test_code_in_a_callout_is_its_own_surface(fixture_page: Page, dark: bool):
    if dark:
        fixture_page.evaluate("document.documentElement.classList.add('dark')")
    colours = fixture_page.evaluate(
        """() => {
          // Composite each element's own fill over the callout's resolved
          // colour, in a canvas, so translucent fills are judged the way they
          // are seen rather than as declared.
          const cv = document.createElement('canvas');
          cv.width = cv.height = 1;
          const ctx = cv.getContext('2d', {willReadFrequently: true});
          const paint = (...fills) => {
            ctx.clearRect(0, 0, 1, 1);
            ctx.fillStyle = getComputedStyle(document.body).backgroundColor;
            ctx.fillRect(0, 0, 1, 1);
            for (const f of fills) { ctx.fillStyle = f; ctx.fillRect(0, 0, 1, 1); }
            return [...ctx.getImageData(0, 0, 1, 1).data.slice(0, 3)];
          };
          const bg = s => getComputedStyle(document.querySelector(s)).backgroundColor;
          const adm = bg('.admonition');
          return {
            callout: paint(adm),
            chip: paint(adm, bg('.admonition > p:not(.admonition-title) code')),
            block: paint(adm, bg('.admonition div.codehilite')),
            prose_block: paint(bg('article .typography > div.codehilite, .tabbed-block div.codehilite')),
          };
        }"""
    )
    dist = lambda a, b: sum(abs(x - y) for x, y in zip(a, b))  # noqa: E731
    assert dist(colours["chip"], colours["callout"]) >= 12, colours
    assert dist(colours["block"], colours["callout"]) >= 12, colours
    # A fenced block keeps the one code surface it has everywhere else.
    assert dist(colours["block"], colours["prose_block"]) <= 3, colours


# Minimum clear paper between a chip and the chip on the next line. Prose was
# 5.4px when an even 0.2rem padding put most of the fill above the capitals;
# a callout's tighter leading made chips overlap outright.
@pytest.mark.parametrize(
    "scope,min_gap",
    [
        ("article .typography > p", 7),
        (".admonition > p:not(.admonition-title)", 1.5),
    ],
)
def test_inline_code_chips_clear_the_next_line(
    fixture_page: Page, scope: str, min_gap: float
):
    m = (
        fixture_page.locator(scope)
        .filter(has=fixture_page.locator("code"))
        .last.evaluate(
            """p => {
          const line = parseFloat(getComputedStyle(p).lineHeight);
          const rects = [...p.querySelectorAll('code')]
            .flatMap(c => [...c.getClientRects()]);
          const tops = [...new Set(rects.map(r => Math.round(r.top)))];
          let overlap = -Infinity;
          for (const a of rects) for (const b of rects) {
            if (b.top - a.top > line / 2) overlap = Math.max(overlap, a.bottom - b.top);
          }
          return {line, height: Math.max(...rects.map(r => r.height)),
                  lines: tops.length, overlap};
        }"""
        )
    )
    assert m["lines"] >= 2, f"fixture must wrap chips onto two lines: {m}"
    # The chip fits inside its own line box ...
    assert m["height"] < m["line"], m
    # ... and leaves paper between it and the chip on the line below.
    assert -m["overlap"] >= min_gap, m
