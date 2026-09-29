"""The paper system: grain on every plane, a distinct rail, one-rule cards.

The grain is a background-image layered over each surface's own colour, so a
typo in the data URI or a later `background:` shorthand that resets
`background-image` drops it without any error — the page just goes flat.

The rail band is the only thing telling navigation from reading once the
flat sidebar fill is gone, so it must stay a different colour from the page.

Cards take the grain, the ink-alpha rule and a soft press shadow, and nothing
else: one 1px border, no inset or dashed second outline, no hard 1px contact
line under the border (which reads as a second rule).
"""

import pytest
from playwright.sync_api import Browser, Page


@pytest.mark.parametrize("dark", [False, True])
def test_paper_planes_rail_band_and_single_rule_cards(
    page: Page, local_deployment: str, dark: bool
):
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(local_deployment + "/mewbo_components/", wait_until="networkidle")
    page.evaluate(
        "dark => document.documentElement.classList.toggle('dark', dark)", dark
    )
    probe = page.evaluate("""() => {
      const grain = (el, pseudo) => !!el &&
        getComputedStyle(el, pseudo).backgroundImage.includes('paper.svg');
      const q = s => document.querySelector(s);
      const band = getComputedStyle(q('[data-slot=sidebar-wrapper]'), '::before');
      const card = document.createElement('div');
      card.className = 'ms-card';
      q('article').append(card);
      const c = getComputedStyle(card);
      return {
        page: grain(q('#inner-body')), footer: grain(q('.mewbo-footer')),
        header: grain(q('.mewbo-header')),
        band: grain(q('[data-slot=sidebar-wrapper]'), '::before'),
        bandColor: band.backgroundColor,
        pageColor: getComputedStyle(q('#inner-body')).backgroundColor,
        card: c.backgroundImage.includes('paper.svg'),
        cardBorder: c.borderTopWidth, cardOutline: c.outlineStyle,
        cardShadow: c.boxShadow,
      };
    }""")
    for plane in ("page", "footer", "header", "band", "card"):
        assert probe[plane], f"{plane} lost its grain: {probe}"
    assert probe["bandColor"] != probe["pageColor"], (
        f"the sidebar band is the page colour, so the rail reads as part of "
        f"the reading column: {probe}"
    )
    assert probe["cardBorder"] == "1px", probe
    assert probe["cardOutline"] == "none", probe
    assert "inset" not in probe["cardShadow"], probe
    # A hard `0 1px 0` shadow under a 1px border is a second rule.
    assert " 0px 1px 0px " not in f" {probe['cardShadow']} ", probe


@pytest.mark.parametrize("width", [390, 768])
def test_touch_targets_do_not_stretch_the_page_actions(
    browser: Browser, local_deployment: str, width: int
):
    """On a coarse pointer the buttons once grew to 44px inside a 32px pill,
    hanging the seam and both hit boxes below the drawn control."""
    with browser.new_context(
        viewport={"width": width, "height": 900}, has_touch=True, is_mobile=True
    ) as context:
        page = context.new_page()
        page.goto(local_deployment + "/", wait_until="networkidle")
        heights = page.evaluate("""() => {
          const root = document.querySelector('[data-mewbo-page-actions]');
          const h = e => Math.round(e.getBoundingClientRect().height);
          return [h(root), ...[...root.querySelectorAll(':scope > button')].map(h),
                  h(document.querySelector('#next-button'))];
        }""")
    assert len(set(heights)) == 1, heights
