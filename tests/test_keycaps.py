"""Keyboard glyphs have one outline and stay legible alongside prose."""

import pytest
from playwright.sync_api import Page


@pytest.mark.parametrize("dark", [False, True])
@pytest.mark.parametrize("width", [390, 1440])
def test_keycaps_have_font_size_and_spacing(
    page: Page, local_deployment: str, dark: bool, width: int
):
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(local_deployment + "/keyboard/", wait_until="networkidle")
    page.evaluate(
        "dark => document.documentElement.classList.toggle('dark', dark)", dark
    )
    metrics = page.locator("article kbd.key-a").first.evaluate("""async key => {
      await document.fonts.ready;
      const s = getComputedStyle(key);
      return {font:s.fontFamily, size:parseFloat(s.fontSize),
        peer:parseFloat(getComputedStyle(key.parentElement).fontSize),
        left:parseFloat(s.marginLeft), right:parseFloat(s.marginRight),
        border:s.borderTopWidth, background:s.backgroundColor,
        padding:s.paddingLeft, loaded:document.fonts.check('26px "Libertinus Keyboard"')};
    }""")
    assert "Libertinus Keyboard" in metrics["font"]
    assert metrics["loaded"]
    assert metrics["size"] == pytest.approx(metrics["peer"] * 1.5725, abs=0.01)
    assert metrics["border"] == "0px"
    assert metrics["background"] == "rgba(0, 0, 0, 0)"
    assert metrics["padding"] == "0px"
    assert metrics["left"] >= 2
    assert metrics["right"] >= 2
    command = page.locator("article .key-command").first
    assert command.inner_text() == "Cmd"
    assert (
        command.evaluate("el => getComputedStyle(el).borderTopWidth") == "1px"
    )
    assert page.locator("article .key-windows").inner_text() == "Win"
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
