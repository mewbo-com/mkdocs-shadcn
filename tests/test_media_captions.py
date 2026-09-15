"""Screenshot and carousel captions share a compact overlay treatment."""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.parametrize("width", [390, 1440])
@pytest.mark.parametrize("dark", [False, True])
def test_media_is_frameless_with_readable_caption_overlays(
    page: Page, local_deployment: str, width: int, dark: bool
):
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(
        local_deployment + "/mewbo_components/", wait_until="networkidle"
    )
    page.evaluate(
        "dark => document.documentElement.classList.toggle('dark', dark)", dark
    )
    page.evaluate("document.querySelector('.ms-shots').swiper.autoplay.stop()")
    for selector in [
        "figure.ms-shot",
        ".ms-shots .swiper-slide-active figure",
    ]:
        figure = page.locator(selector)
        metrics = figure.evaluate("""figure => {
          const image = figure.querySelector('img');
          const caption = figure.querySelector('figcaption');
          const box = figure.getBoundingClientRect();
          const img = image.getBoundingClientRect();
          const cap = caption.getBoundingClientRect();
          return {
            width: box.width, height: box.height,
            imageWidth: img.width, imageHeight: img.height,
            imageTop: img.top, imageBottom: img.bottom,
            captionTop: cap.top, captionBottom: cap.bottom,
            centered: Math.abs(cap.left + cap.width / 2 - img.left - img.width / 2),
            border: getComputedStyle(figure).borderTopWidth,
            padding: getComputedStyle(image).paddingTop,
            background: getComputedStyle(caption).backgroundColor,
            color: getComputedStyle(caption).color,
          };
        }""")
        assert metrics["border"] == "0px", metrics
        assert metrics["padding"] == "0px", metrics
        assert abs(metrics["width"] - metrics["imageWidth"]) < 2, metrics
        assert abs(metrics["height"] - metrics["imageHeight"]) < 2, metrics
        assert metrics["imageTop"] <= metrics["captionTop"], metrics
        assert metrics["captionBottom"] <= metrics["imageBottom"] + 1, metrics
        assert metrics["centered"] < 2, metrics
        assert metrics["background"] == "rgb(0, 0, 0)", metrics
        assert metrics["color"] == "rgb(255, 255, 255)", metrics
        expect(figure.locator("figcaption")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_carousel_keeps_widescreen_frame(page: Page, local_deployment: str):
    page.goto(
        local_deployment + "/mewbo_components/", wait_until="networkidle"
    )
    image = page.locator(".ms-shots .swiper-slide-active img")
    assert image.evaluate("""image => {
      const rect = image.getBoundingClientRect();
      return Math.abs(rect.width / rect.height - 16 / 9) < 0.01 && getComputedStyle(image).objectFit === 'cover';
    }""")


def test_carousel_keeps_caption_when_slide_changes(
    page: Page, local_deployment: str
):
    page.goto(
        local_deployment + "/mewbo_components/", wait_until="networkidle"
    )
    before = page.locator(".ms-shots .swiper-wrapper").bounding_box()
    page.evaluate("""() => {
      const swiper = document.querySelector('.ms-shots').swiper;
      swiper.autoplay.stop();
      swiper.slideNext(0);
    }""")
    after = page.locator(".ms-shots .swiper-wrapper").bounding_box()
    assert after["height"] == pytest.approx(before["height"], abs=1)
    caption = page.locator(".ms-shots .swiper-slide-active figcaption")
    expect(caption).to_have_text("Second slide")
    expect(caption).to_be_visible()
    assert caption.evaluate("""caption => {
      const image = caption.parentElement.querySelector('img').getBoundingClientRect();
      return caption.getBoundingClientRect().bottom <= image.bottom + 1;
    }""")
