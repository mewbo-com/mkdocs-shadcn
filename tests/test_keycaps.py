"""Keycaps load their local font and keep readable shortcut spacing."""

from playwright.sync_api import Page


def test_keycaps_have_font_size_and_spacing(page: Page, local_deployment: str):
    page.goto(local_deployment + "/keyboard/", wait_until="networkidle")
    metrics = page.locator("article kbd").first.evaluate("""async key => {
      await document.fonts.ready;
      const s = getComputedStyle(key);
      return {font:s.fontFamily, size:parseFloat(s.fontSize),
        left:parseFloat(s.marginLeft), right:parseFloat(s.marginRight),
        loaded:document.fonts.check('13.3333px "Libertinus Keyboard"')};
    }""")
    assert "Libertinus Keyboard" in metrics["font"]
    assert metrics["loaded"]
    assert metrics["size"] >= 13.3
    assert metrics["left"] >= 2
    assert metrics["right"] >= 2
    assert page.locator("article .key-command").first.inner_text() == "Cmd"
    assert page.locator("article .key-windows").inner_text() == "Win"
