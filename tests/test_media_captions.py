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
            captionPaddingY: parseFloat(getComputedStyle(caption).paddingTop),
            captionPaddingX: parseFloat(getComputedStyle(caption).paddingLeft),
          };
        }""")
        assert metrics["border"] == "0px", metrics
        assert metrics["padding"] == "0px", metrics
        assert abs(metrics["width"] - metrics["imageWidth"]) < 2, metrics
        assert abs(metrics["height"] - metrics["imageHeight"]) < 2, metrics
        assert metrics["imageTop"] <= metrics["captionTop"], metrics
        assert metrics["captionBottom"] <= metrics["imageBottom"] + 1, metrics
        assert metrics["centered"] < 2, metrics
        assert metrics["color"] == "rgb(255, 255, 255)", metrics
        # A pill needs more side padding than end padding, but it still has to
        # read as a caption rather than a banner.
        assert metrics["captionPaddingY"] <= 8, metrics
        assert metrics["captionPaddingX"] <= 16, metrics
        assert metrics["captionPaddingX"] > metrics["captionPaddingY"], metrics
        expect(figure.locator("figcaption")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def _rgba(value: str) -> tuple[float, float, float, float]:
    """Parse a computed `rgb()`/`rgba()` colour into channels plus alpha."""
    parts = [
        float(p)
        for p in value[value.index("(") + 1 : -1]
        .replace("/", " ")
        .replace(",", " ")
        .split()
    ]
    r, g, b = parts[:3]
    return r, g, b, (parts[3] if len(parts) > 3 else 1.0)


def _relative_luminance(r: float, g: float, b: float) -> float:
    def channel(c: float) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast(
    fg: tuple[float, float, float], bg: tuple[float, float, float]
) -> float:
    a, b = _relative_luminance(*fg), _relative_luminance(*bg)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.parametrize(
    "selector", ["figure.ms-shot", ".ms-shots .swiper-slide-active figure"]
)
def test_caption_is_a_translucent_blurred_pill(
    page: Page, local_deployment: str, selector: str
):
    """The caption sits in its own frosted-glass pill, not a black bar.

    Three things make it a pill of glass rather than a rectangle of paint:
    a fully-rounded end cap, a background that lets the image through, and a
    backdrop blur so what shows through never competes with the text.
    """
    page.goto(
        local_deployment + "/mewbo_components/", wait_until="networkidle"
    )
    page.evaluate("document.querySelector('.ms-shots').swiper.autoplay.stop()")
    caption = page.locator(selector).locator("figcaption")
    style = caption.evaluate("""caption => {
      const css = getComputedStyle(caption);
      const box = caption.getBoundingClientRect();
      return {
        radius: css.borderTopLeftRadius,
        height: box.height,
        background: css.backgroundColor,
        backdrop: css.backdropFilter || css.webkitBackdropFilter,
        border: css.borderTopWidth,
        borderColor: css.borderTopColor,
      };
    }""")

    # Pill: the end cap is a semicircle, so the radius covers half the height.
    assert style["radius"].endswith("px"), style
    assert float(style["radius"][:-2]) >= style["height"] / 2 - 0.5, style

    # Glass: translucent enough to see the image, opaque enough to darken it.
    red, green, blue, alpha = _rgba(style["background"])
    assert 0.3 <= alpha <= 0.85, style
    assert _relative_luminance(red, green, blue) < 0.1, style

    # Glass: the image behind it is blurred rather than merely tinted.
    assert "blur(" in style["backdrop"], style


@pytest.mark.parametrize(
    "selector", ["figure.ms-shot", ".ms-shots .swiper-slide-active figure"]
)
def test_caption_text_stays_readable_over_any_image(
    page: Page, local_deployment: str, selector: str
):
    """White caption text clears WCAG AA against the worst image behind it.

    The pill is translucent, so the composited backdrop depends on the photo.
    A pure-white image is the worst case: it lightens the pill the most. If
    contrast holds there, it holds everywhere, blur included -- blurring only
    averages pixels, so it can never exceed that bound.
    """
    page.goto(
        local_deployment + "/mewbo_components/", wait_until="networkidle"
    )
    page.evaluate("document.querySelector('.ms-shots').swiper.autoplay.stop()")
    caption = page.locator(selector).locator("figcaption")
    style = caption.evaluate("""caption => {
      const css = getComputedStyle(caption);
      return {background: css.backgroundColor, color: css.color};
    }""")

    red, green, blue, alpha = _rgba(style["background"])
    worst_case = tuple(
        channel * alpha + 255 * (1 - alpha) for channel in (red, green, blue)
    )
    text = _rgba(style["color"])[:3]
    ratio = _contrast(text, worst_case)
    assert ratio >= 4.5, {"ratio": ratio, "over_white": worst_case, **style}


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
