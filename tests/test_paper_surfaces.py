"""Reading surfaces carry the paper grain; cards keep their single rule.

The grain is a background-image layered over each surface's own colour, so a
typo in the data URI or a later `background:` shorthand that resets
`background-image` drops it without any error — the page just goes flat.

Cards take the grain and the ink-alpha rule, and nothing else: one 1px border,
no inset or dashed second outline. That structure is a deliberate choice, and
this is what keeps a later port of the source system from reintroducing it.
"""

import pytest
from playwright.sync_api import Page


@pytest.mark.parametrize("dark", [False, True])
def test_reading_surfaces_carry_the_grain_and_cards_one_rule(
    page: Page, local_deployment: str, dark: bool
):
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(local_deployment + "/mewbo_components/", wait_until="networkidle")
    page.evaluate(
        "dark => document.documentElement.classList.toggle('dark', dark)", dark
    )
    probe = page.evaluate("""() => {
      const cs = s => { const e = document.querySelector(s);
                        return e ? getComputedStyle(e) : null; };
      const grain = s => { const c = cs(s);
                           return !!c && c.backgroundImage.includes('feTurbulence'); };
      const card = document.createElement('div');
      card.className = 'ms-card';
      document.querySelector('article').append(card);
      const c = getComputedStyle(card);
      return {
        page: grain('#inner-body'), footer: grain('.mewbo-footer'),
        header: grain('.mewbo-header'),
        card: c.backgroundImage.includes('feTurbulence'),
        cardBorder: c.borderTopWidth, cardOutline: c.outlineStyle,
        cardShadow: c.boxShadow,
      };
    }""")
    assert probe["page"] and probe["footer"] and probe["card"], probe
    # The header is chrome on its own plane; grain there flattens that step.
    assert not probe["header"], probe
    assert probe["cardBorder"] == "1px", probe
    assert probe["cardOutline"] == "none", probe
    assert "inset" not in probe["cardShadow"], probe
