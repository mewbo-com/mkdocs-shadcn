"""Fullscreen image controls remain readable and usable on every screen."""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.parametrize("width", [390, 1440])
def test_lightbox_controls_and_caption(
    page: Page, local_deployment: str, width: int
):
    page.set_viewport_size({"width": width, "height": 900})
    page.goto(
        local_deployment + "/mewbo_components/", wait_until="networkidle"
    )
    page.wait_for_function("document.querySelector('.ms-shots').swiper")
    page.evaluate("document.querySelector('.ms-shots').swiper.autoplay.stop()")
    page.locator(".ms-shots .swiper-slide-active img").click()
    viewer = page.locator(".glightbox-container")
    expect(viewer).to_be_visible()
    close = viewer.locator(".gclose")
    assert close.evaluate("el => el.getBoundingClientRect().height") >= 44
    assert (
        close.evaluate("el => getComputedStyle(el, '::after').content")
        == '"Close"'
    )
    caption = viewer.locator(".gslide.current .gslide-desc")
    expect(caption).to_have_text("First slide")
    assert (
        caption.evaluate("el => getComputedStyle(el).color")
        == "rgb(255, 255, 255)"
    )
    assert (
        caption.evaluate("el => getComputedStyle(el).backgroundColor")
        != "rgba(0, 0, 0, 0)"
    )
    image = viewer.locator(".gslide.current .gslide-image img")
    expect(image).to_be_visible()
    page.wait_for_function("""() => {
      const image = document.querySelector('.gslide.current .gslide-image img');
      if (!image) return false;
      const r = image.getBoundingClientRect();
      const maxW = innerWidth - (innerWidth <= 640 ? 24 : 144);
      const maxH = innerHeight - 200;
      const expected = Math.min(maxW / image.naturalWidth, maxH / image.naturalHeight);
      return Math.abs(r.width - image.naturalWidth * expected) < 3
        && Math.abs(r.height - image.naturalHeight * expected) < 3;
    }""")
    assert "blur(" in viewer.locator(".goverlay").evaluate(
        "el => getComputedStyle(el).backdropFilter || getComputedStyle(el).webkitBackdropFilter"
    )
    rect = image.bounding_box()
    assert rect["x"] >= 0 and rect["x"] + rect["width"] <= width + 1
    assert close.bounding_box()["y"] + 44 <= rect["y"] + 1
    page.set_viewport_size({"width": 900, "height": 400})
    page.wait_for_function("""() => {
      const image = document.querySelector('.gslide.current .gslide-image img');
      const r = image.getBoundingClientRect();
      return r.height <= 201 && r.top >= 0 && r.bottom <= innerHeight;
    }""")
    page.keyboard.press("ArrowRight")
    expect(viewer.locator(".gslide.current .gslide-desc")).to_have_text(
        "Second slide"
    )
    close.click()
    expect(viewer).not_to_be_visible()
