"""Every reading surface sits on the theme's four-rung leading ladder.

The page read as cramped not because any one value was wrong but because the
values had drifted apart: paragraphs were already generous at 1.625 while
everything read alongside them lagged — list items at 1.5, admonitions and
captions at 1.4-1.43, the ToC at 1.4. A reader does not experience those as
separate components, so the mix reads as unevenly tight.

What this pins is the ORDERING and the floor, not the exact numbers: prose is
the loosest, chrome sits below it, code below that, headings tightest. Anyone
is free to retune a rung; nobody should be able to leave one surface behind
again, which is what happened here and what no build step would catch.
"""

import pytest
from playwright.sync_api import Page

# Ratios are read as line-height / font-size, so they hold regardless of the
# responsive type scale (body copy is 15px at 1440 and 16.8px at 390).
BODY_FLOOR = 1.65
CHROME_FLOOR = 1.5


@pytest.mark.parametrize("width", [390, 1440])
def test_prose_surfaces_share_the_body_rung(
    page: Page, local_deployment: str, width: int
):
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(
        local_deployment + "/table_wrap_regression/", wait_until="networkidle"
    )

    ratios = page.evaluate(
        """async () => {
          await document.fonts.ready;
          const ratio = sel => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const s = getComputedStyle(el);
            return parseFloat(s.lineHeight) / parseFloat(s.fontSize);
          };
          return {
            p: ratio('article .typography p'),
            li: ratio('article .typography li'),
            // The wrapped prose cell, which got its own fix in v1.22.1 and
            // must not be quietly pulled back down by a later rule.
            cell: ratio('article table:not(.codehilitetable) tbody td'),
          };
        }"""
    )

    for name, value in ratios.items():
        assert value is not None, f"no {name} on the fixture page"
        assert value >= BODY_FLOOR, (
            f"{name} is set at {value:.2f} leading, under the body rung "
            f"({BODY_FLOOR}) — it has been left behind the prose around it"
        )


@pytest.mark.parametrize("width", [1440])
def test_leading_ladder_is_ordered(
    page: Page, local_deployment: str, width: int
):
    """Prose loosest, then chrome, then code, then headings.

    Asserted as an ordering rather than as four fixed numbers: the rungs are
    a design decision and may be retuned, but a heading must never end up
    looser than body copy, and code must never end up looser than prose.
    """
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(local_deployment + "/get_started/", wait_until="networkidle")

    r = page.evaluate(
        """async () => {
          await document.fonts.ready;
          const ratio = sel => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const s = getComputedStyle(el);
            return parseFloat(s.lineHeight) / parseFloat(s.fontSize);
          };
          return {
            body: ratio('article .typography p'),
            chrome: ratio('.mewbo-toc__link'),
            code: ratio('article div.codehilite pre'),
            heading: ratio('article .typography h3'),
          };
        }"""
    )

    missing = [k for k, v in r.items() if v is None]
    assert not missing, f"could not measure {missing} — check the fixture page"

    assert r["body"] > r["chrome"], (
        f"body copy ({r['body']:.2f}) is not looser than chrome "
        f"({r['chrome']:.2f}) — the ladder is inverted"
    )
    assert r["chrome"] >= r["code"], (
        f"chrome ({r['chrome']:.2f}) is tighter than code ({r['code']:.2f})"
    )
    assert r["code"] > r["heading"], (
        f"code ({r['code']:.2f}) is not looser than display type "
        f"({r['heading']:.2f})"
    )

    # Chrome still has to be comfortable — the ordering alone would be
    # satisfied by a 1.0 ToC under a 1.05 paragraph.
    assert r["chrome"] >= CHROME_FLOOR, (
        f"chrome text is set at {r['chrome']:.2f}, under the floor "
        f"({CHROME_FLOOR}) — a wrapped ToC entry reads as cramped"
    )

    # Headings are display type: generous leading splits a two-line heading
    # into what looks like two headings.
    assert r["heading"] < 1.4, (
        f"headings are set at {r['heading']:.2f} — too loose to hold a "
        "two-line heading together as one phrase"
    )
