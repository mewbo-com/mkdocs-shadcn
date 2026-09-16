"""Full screen means full screen, on a phone as much as on a desktop.

The previous viewer reserved a flat 200px of height for its close button and
caption and inset the sides by 144px, so a picture opened on a phone filled
under a third of the screen. Chrome floats over the image now, so the only
limits are the viewport and the image's own pixels.
"""

import pytest
from playwright.sync_api import Page, expect

PHONE = {"width": 390, "height": 844}
PHONE_LANDSCAPE = {"width": 844, "height": 390}
TABLET = {"width": 768, "height": 1024}
DESKTOP = {"width": 1440, "height": 900}

MOUNTED = "document.querySelector('.ms-shots').swiper"

IMAGE_BOX = """() => {
  const img = document.querySelector('.viewer-canvas img');
  if (!img || !img.naturalWidth) return null;
  const r = img.getBoundingClientRect();
  return {
    width: r.width, height: r.height, top: r.top, left: r.left,
    bottom: r.bottom, right: r.right,
    naturalWidth: img.naturalWidth, naturalHeight: img.naturalHeight,
    vw: window.innerWidth, vh: window.innerHeight,
  };
}"""


def _open_viewer(page: Page, local_deployment: str, viewport: dict):
    page.set_viewport_size(viewport)
    page.goto(
        local_deployment + "/mewbo_components/", wait_until="networkidle"
    )
    page.wait_for_function(MOUNTED)
    page.evaluate("document.querySelector('.ms-shots').swiper.autoplay.stop()")
    page.locator(".ms-shots .swiper-slide-active img").click()
    page.wait_for_selector(".viewer-container.viewer-in")
    page.wait_for_function(f"({IMAGE_BOX})() !== null")
    page.wait_for_timeout(400)
    return page.evaluate(IMAGE_BOX)


@pytest.mark.parametrize(
    "viewport,name",
    [
        (PHONE, "phone portrait"),
        (PHONE_LANDSCAPE, "phone landscape"),
        (TABLET, "tablet"),
        (DESKTOP, "desktop"),
    ],
)
def test_image_claims_the_screen(
    page: Page, local_deployment: str, viewport: dict, name: str
):
    """The image uses the space it is given, up to its own resolution.

    It should touch at least one axis of the viewport, minus a small margin —
    the old viewer topped out at 31% of a phone screen.
    """
    box = _open_viewer(page, local_deployment, viewport)
    # What the image could occupy: the viewport, capped by its own pixels.
    fit = min(
        box["vw"] / box["naturalWidth"], box["vh"] / box["naturalHeight"], 1
    )
    ideal_w = box["naturalWidth"] * fit
    ideal_h = box["naturalHeight"] * fit
    assert box["width"] >= ideal_w * 0.85, (
        f"{name}: image is {box['width']:.0f}px wide, could be {ideal_w:.0f}px"
    )
    assert box["height"] >= ideal_h * 0.85, (
        f"{name}: image is {box['height']:.0f}px tall, "
        f"could be {ideal_h:.0f}px"
    )


@pytest.mark.parametrize(
    "viewport,name", [(PHONE, "phone"), (DESKTOP, "desktop")]
)
def test_image_is_never_upscaled(
    page: Page, local_deployment: str, viewport: dict, name: str
):
    """Full size means the image's own size, never larger.

    Carried over from the previous viewer: blowing a small screenshot up to
    fill a big monitor shows it blurry.
    """
    box = _open_viewer(page, local_deployment, viewport)
    assert box["width"] <= box["naturalWidth"] + 1, (
        f"{name}: image upscaled past its natural width"
    )
    assert box["height"] <= box["naturalHeight"] + 1, (
        f"{name}: image upscaled past its natural height"
    )


@pytest.mark.parametrize(
    "viewport,name", [(PHONE, "phone"), (DESKTOP, "desktop")]
)
def test_image_stays_within_the_viewport(
    page: Page, local_deployment: str, viewport: dict, name: str
):
    """Nothing is cropped off an edge."""
    box = _open_viewer(page, local_deployment, viewport)
    assert box["left"] >= -1 and box["top"] >= -1, f"{name}: image overflows"
    assert box["right"] <= box["vw"] + 1, f"{name}: image overflows right"
    assert box["bottom"] <= box["vh"] + 1, f"{name}: image overflows bottom"


def test_chrome_floats_over_the_image(page: Page, local_deployment: str):
    """Controls overlay the picture instead of taking a slice of the screen.

    This is the fix for the reported bug: the old chrome was laid out beside
    the image, so the image could never use the full screen.
    """
    box = _open_viewer(page, local_deployment, PHONE)
    for selector in (".viewer-toolbar", ".viewer-title"):
        chrome = page.locator(selector)
        if chrome.count() == 0 or not chrome.first.is_visible():
            continue
        assert (
            chrome.first.evaluate("el => getComputedStyle(el).position")
            == "absolute"
        ), f"{selector} is not floating"
    # The image reaches the full width it is entitled to despite the chrome.
    assert box["width"] >= min(box["vw"], box["naturalWidth"]) * 0.85


def test_viewer_walks_the_carousel(page: Page, local_deployment: str):
    """Arrows step through every slide of the strip, not just the one clicked."""
    _open_viewer(page, local_deployment, DESKTOP)
    expect(page.locator(".viewer-title")).to_contain_text("First slide")
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(600)
    expect(page.locator(".viewer-title")).to_contain_text("Second slide")
    page.keyboard.press("ArrowLeft")
    page.wait_for_timeout(600)
    expect(page.locator(".viewer-title")).to_contain_text("First slide")


def test_viewer_closes(page: Page, local_deployment: str):
    """Escape puts the reader back on the page."""
    _open_viewer(page, local_deployment, DESKTOP)
    page.keyboard.press("Escape")
    page.wait_for_timeout(600)
    expect(page.locator(".viewer-container.viewer-in")).to_have_count(0)
