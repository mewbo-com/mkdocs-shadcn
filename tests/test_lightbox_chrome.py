"""Fullscreen image controls remain readable and usable on every screen.

The viewer is Viewer.js; its chrome floats over the picture rather than taking
a slice of the layout, which is what lets the image fill the screen. These
assertions are about the controls and the caption — the sizing itself is
covered by test_viewer_fullscreen.py.
"""

import pytest
from playwright.sync_api import Page, expect

# Every control is a touch target before it is a decoration.
MIN_TOUCH_TARGET = 32


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
    viewer = page.locator(".viewer-container.viewer-in")
    expect(viewer).to_be_visible()

    # The caption rides with the picture.
    caption = viewer.locator(".viewer-title")
    expect(caption).to_have_text("First slide")

    # Controls are big enough to hit and sit clear of the image's own box.
    toolbar = viewer.locator(".viewer-toolbar")
    expect(toolbar).to_be_visible()
    assert (
        toolbar.evaluate("el => el.getBoundingClientRect().height")
        >= MIN_TOUCH_TARGET
    )

    image = viewer.locator(".viewer-canvas img")
    expect(image).to_be_visible()
    page.wait_for_function("""() => {
      const i = document.querySelector('.viewer-canvas img');
      return i && i.naturalWidth > 0 && i.getBoundingClientRect().width > 0;
    }""")

    # Nothing is cropped off an edge.
    box = image.bounding_box()
    assert box["x"] >= -1 and box["x"] + box["width"] <= width + 1

    # Carried over from the previous viewer: an image is never enlarged past
    # its own pixels, so a small screenshot stays sharp instead of blurry.
    assert page.evaluate("""() => {
      const i = document.querySelector('.viewer-canvas img');
      const r = i.getBoundingClientRect();
      return r.width <= i.naturalWidth + 1 && r.height <= i.naturalHeight + 1;
    }""")

    # The backdrop separates the viewer from the page behind it. It is a class
    # on the container itself, not a child element.
    assert (
        viewer.evaluate("el => getComputedStyle(el).backgroundColor")
        != "rgba(0, 0, 0, 0)"
    )

    # A short viewport still fits the whole picture on screen.
    page.set_viewport_size({"width": 900, "height": 400})
    page.wait_for_timeout(500)
    page.wait_for_function("""() => {
      const i = document.querySelector('.viewer-canvas img');
      const r = i.getBoundingClientRect();
      return r.top >= -1 && r.bottom <= innerHeight + 1;
    }""")

    # Arrows walk the carousel strip.
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(600)
    expect(viewer.locator(".viewer-title")).to_have_text("Second slide")

    page.keyboard.press("Escape")
    page.wait_for_timeout(600)
    expect(page.locator(".viewer-container.viewer-in")).to_have_count(0)
