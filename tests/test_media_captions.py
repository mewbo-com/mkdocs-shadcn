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
            gradient: getComputedStyle(caption).backgroundImage,
            shadow: getComputedStyle(caption).textShadow,
          };
        }""")
        assert metrics["border"] == "0px", metrics
        assert metrics["padding"] == "0px", metrics
        assert abs(metrics["width"] - metrics["imageWidth"]) < 2, metrics
        assert abs(metrics["height"] - metrics["imageHeight"]) < 2, metrics
        assert metrics["imageTop"] <= metrics["captionTop"], metrics
        assert metrics["captionBottom"] <= metrics["imageBottom"] + 1, metrics
        assert metrics["centered"] < 2, metrics
        assert "linear-gradient" in metrics["gradient"], metrics
        assert metrics["shadow"] != "none", metrics
        expect(figure.locator("figcaption")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_caption_halo_surrounds_text_without_blurring_letters(
    page: Page, local_deployment: str
):
    page.goto(
        local_deployment + "/mewbo_components/", wait_until="networkidle"
    )
    for selector in [".ms-shot > figcaption", ".ms-shots figcaption"]:
        halo = page.locator(selector).first.evaluate("""caption => {
          const style = getComputedStyle(caption);
          const layers = style.textShadow.split(/,(?![^()]*\\))/).map(layer => {
            const color = layer.match(/rgba?\\(([^)]+)\\)/);
            const rgba = color ? color[1].split(',').map(Number) : [];
            const lengths = layer.replace(/rgba?\\([^)]+\\)/, '')
              .match(/-?[\\d.]+px/g)?.map(parseFloat) || [];
            return { x: lengths[0], y: lengths[1], blur: lengths[2],
              dark: rgba.slice(0, 3).every(c => c === 0),
              alpha: rgba.length === 4 ? rgba[3] : 1 };
          });
          return { layers, filter: style.filter };
        }""")
        tight = [
            layer
            for layer in halo["layers"]
            if layer["dark"] and layer["alpha"] >= 0.9 and layer["blur"] <= 2
        ]
        assert any(layer["x"] < 0 for layer in tight), halo
        assert any(layer["x"] > 0 for layer in tight), halo
        assert any(layer["y"] < 0 for layer in tight), halo
        assert any(layer["y"] > 0 for layer in tight), halo
        assert any(
            layer["dark"]
            and layer["alpha"] >= 0.8
            and 3 <= layer["blur"] <= 10
            for layer in halo["layers"]
        ), halo
        assert halo["filter"] == "none", halo


def test_carousel_uses_image_ratio_without_letterboxing(
    page: Page, local_deployment: str
):
    page.goto(
        local_deployment + "/mewbo_components/", wait_until="networkidle"
    )
    image = page.locator(".ms-shots .swiper-slide-active img")
    assert image.evaluate("""image => {
      const rect = image.getBoundingClientRect();
      return Math.abs(rect.width / rect.height - image.naturalWidth / image.naturalHeight) < 0.01;
    }""")


def test_carousel_keeps_caption_when_slide_changes(
    page: Page, local_deployment: str
):
    page.goto(
        local_deployment + "/mewbo_components/", wait_until="networkidle"
    )
    page.evaluate("""() => {
      const swiper = document.querySelector('.ms-shots').swiper;
      swiper.autoplay.stop();
      swiper.slideNext(0);
    }""")
    caption = page.locator(".ms-shots .swiper-slide-active figcaption")
    expect(caption).to_have_text("Second slide")
    expect(caption).to_be_visible()
    assert caption.evaluate("""caption => {
      const image = caption.parentElement.querySelector('img').getBoundingClientRect();
      return caption.getBoundingClientRect().bottom <= image.bottom + 1;
    }""")
