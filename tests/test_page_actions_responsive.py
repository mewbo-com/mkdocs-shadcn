"""Page actions stay on-screen and form one connected split control."""

import pytest
from playwright.sync_api import Browser, Page, expect

TOGGLE = "[data-mewbo-page-actions-toggle]"
MENU = "[data-mewbo-page-actions-menu]"


def assert_menu_usable(page: Page):
    menu = page.locator(MENU)
    expect(menu).to_be_visible()
    geometry = menu.evaluate("""menu => {
      const r = menu.getBoundingClientRect();
      const toggle = document.querySelector('[data-mewbo-page-actions-toggle]')
        .getBoundingClientRect();
      const rows = [...menu.querySelectorAll('[role=menuitem]')];
      return {left:r.left, right:r.right, top:r.top, bottom:r.bottom,
        width:document.documentElement.clientWidth, height:innerHeight,
        gap:Math.min(Math.abs(r.top-toggle.bottom), Math.abs(toggle.top-r.bottom)),
        reachable:rows.filter(row => {
          const b = row.getBoundingClientRect();
          return b.y+b.height/2 > r.top && b.y+b.height/2 < r.bottom;
        }).every(row => {
          const b = row.getBoundingClientRect();
          const hit = document.elementFromPoint(b.x+b.width/2, b.y+b.height/2);
          return hit && row.contains(hit);
        })};
    }""")
    assert geometry["left"] >= 0, geometry
    assert geometry["right"] <= geometry["width"], geometry
    assert geometry["top"] >= 0, geometry
    assert geometry["bottom"] <= geometry["height"], geometry
    assert geometry["gap"] <= 12, geometry
    assert geometry["reachable"], geometry


@pytest.mark.parametrize(
    "size",
    [
        (320, 740),
        (390, 844),
        (639, 800),
        (640, 800),
        (768, 1024),
        (844, 390),
        (1440, 900),
    ],
)
def test_touch_menu_stays_anchored_and_tappable(
    browser: Browser, local_deployment: str, size: tuple
):
    with browser.new_context(
        viewport={"width": size[0], "height": size[1]}, has_touch=True
    ) as context:
        page = context.new_page()
        page.add_init_script("""Object.defineProperty(navigator, 'clipboard', {
          value: {writeText: async text => { window.copiedText = text; }},
          configurable: true
        });""")
        page.goto(local_deployment + "/get_started/", wait_until="networkidle")
        page.locator(TOGGLE).tap()
        assert_menu_usable(page)
        # Short landscape viewports scroll the menu, not the whole page.
        for item in page.locator(MENU + " [role=menuitem]").all():
            item.scroll_into_view_if_needed()
            assert item.evaluate("""row => {
              const b=row.getBoundingClientRect();
              const hit=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2);
              return hit && row.contains(hit);
            }""")
        page.locator("[data-mewbo-copy-proxy]").tap(timeout=3000)
        expect(page.locator("[data-copy-markdown]")).to_have_attribute(
            "data-copy-state", "copied"
        )
        assert page.evaluate("window.copiedText") == page.locator(
            "[data-copy-markdown]"
        ).get_attribute("data-copy-markdown")
        expect(page.locator(MENU)).to_be_hidden()
        page.locator(TOGGLE).tap()
        page.keyboard.press("Escape")
        expect(page.locator(MENU)).to_be_hidden()
        expect(page.locator(TOGGLE)).to_be_focused()


@pytest.mark.parametrize("width", [390, 768, 1440])
@pytest.mark.parametrize("dark", [False, True])
def test_split_control_reads_as_one_control_with_a_flat_seam(
    page: Page, local_deployment: str, width: int, dark: bool
):
    """The two halves join seamlessly and share one surface.

    This used to also assert a 1px outer border and a 1px seam, because the
    control was outlined. It is now filled to match the prev/next arrows it
    sits beside (see
    `test_page_actions.py::test_split_button_matches_its_neighbouring_arrows`),
    so the seam is an inset shadow rather than a border and there is no outer
    border at all. What the test is actually for is unchanged: the halves must
    not drift apart, round against each other, or paint different fills.
    """
    page.set_viewport_size({"width": width, "height": 900})
    page.goto(local_deployment + "/get_started/", wait_until="networkidle")
    page.evaluate(
        "dark => document.documentElement.classList.toggle('dark', dark)", dark
    )
    metrics = page.locator("[data-mewbo-page-actions]").evaluate("""root => {
      const main=root.querySelector('[data-copy-markdown]');
      const toggle=root.querySelector('[data-mewbo-page-actions-toggle]');
      const m=getComputedStyle(main), t=getComputedStyle(toggle), s=getComputedStyle(root);
      const a=main.getBoundingClientRect(), b=toggle.getBoundingClientRect();
      return {gap:b.left-a.right, top:a.top-b.top, height:a.height-b.height,
        inner:[m.borderTopRightRadius,m.borderBottomRightRadius,
               t.borderTopLeftRadius,t.borderBottomLeftRadius].map(parseFloat),
        border:parseFloat(s.borderTopWidth),
        seam:t.boxShadow,
        mainBg:m.backgroundColor, toggleBg:t.backgroundColor};
    }""")
    assert metrics["inner"] == [0, 0, 0, 0], metrics
    assert abs(metrics["gap"]) < 0.5, metrics
    assert abs(metrics["top"]) < 0.5, metrics
    assert abs(metrics["height"]) < 0.5, metrics
    assert metrics["border"] == 0, metrics
    # An inset shadow, not a border: the halves sit on one filled surface, so
    # the divider has to be drawn inside rather than between them.
    assert "inset" in metrics["seam"], metrics
    assert metrics["mainBg"] == metrics["toggleBg"], metrics
    backgrounds = []
    for selector in ("[data-copy-markdown]", TOGGLE):
        button = page.locator(selector)
        button.hover()
        page.wait_for_timeout(180)
        backgrounds.append(
            button.evaluate("el => getComputedStyle(el).backgroundColor")
        )
    assert backgrounds[0] == backgrounds[1], backgrounds


def test_open_menu_follows_resize_and_scroll(
    page: Page, local_deployment: str
):
    page.set_viewport_size({"width": 768, "height": 900})
    page.goto(local_deployment + "/get_started/", wait_until="networkidle")
    page.locator(TOGGLE).click()
    page.mouse.move(5, 600)
    assert_menu_usable(page)
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(100)
    assert_menu_usable(page)
    page.evaluate("window.scrollBy(0, 50)")
    page.wait_for_timeout(100)
    assert_menu_usable(page)
    page.mouse.click(5, 700)
    expect(page.locator(MENU)).to_be_hidden()
