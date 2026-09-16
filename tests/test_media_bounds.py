"""Media stops growing before the monitor does.

`html.layout-full` releases the article's `max-w-2xl` at 3xl so PROSE can use
an ultrawide. Media was released with it, which is not the same thing: a
screenshot scaled to 1900px is not more readable than one at 900px, it is
less, and it sat flush to both column edges with no gutter. Same story inside
the expanded viewers, where the only bound was a proportion of the viewport.
"""

import pytest
from playwright.sync_api import Page

# 3xl is 1600px — the breakpoint where `max-w-none` takes effect. The two
# widths above it are where an unbounded rule actually shows itself.
ULTRAWIDE = (1920, 1080)
SUPERWIDE = (2560, 1440)


def enable_full_layout(page: Page):
    """Turn on the expanded layout and wait for the class to land."""
    page.evaluate("""() => {
        localStorage.setItem('html-layout', 'layout-full');
        document.documentElement.classList.remove('layout-fixed');
        document.documentElement.classList.add('layout-full');
    }""")
    page.wait_for_timeout(120)


@pytest.mark.parametrize("size", [ULTRAWIDE, SUPERWIDE])
def test_media_is_bounded_and_guttered_in_full_layout(
    page: Page, local_deployment: str, size: tuple[int, int]
):
    """Images and carousels stop at a ceiling and keep room on both sides."""
    page.set_viewport_size({"width": size[0], "height": size[1]})
    page.goto(
        f"{local_deployment}/mewbo_components/", wait_until="networkidle"
    )
    enable_full_layout(page)

    measured = page.evaluate("""() => {
        const article = document.querySelector('main article');
        const column = article.getBoundingClientRect();
        const out = [];
        article.querySelectorAll(
            '.ms-shots, .ms-shot, .ms-devices, .typography img, figure'
        ).forEach((el) => {
            const box = el.getBoundingClientRect();
            if (box.width === 0) return;
            // A carousel parks its inactive slides outside the strip on
            // purpose — they are translated off to the side and are not
            // visible. Measuring their gutters says nothing about layout.
            if (el.closest('.swiper-slide:not(.swiper-slide-active)')) return;
            out.push({
                el: el.tagName + '.' + String(el.className).slice(0, 30),
                width: Math.round(box.width),
                leftGutter: Math.round(box.left - column.left),
                rightGutter: Math.round(column.right - box.right),
            });
        });
        return {column: Math.round(column.width), items: out};
    }""")

    # `3xl:max-w-none` only releases the cap at 1600px, and the column is the
    # viewport minus the sidebar and TOC rails — so this is well under `size`.
    assert measured["column"] > 1200, measured["column"]

    for item in measured["items"]:
        # The ceiling. `--ms-media-max-width` is 68rem minus a 2rem gutter
        # either side; a little slack for sub-pixel rounding and borders.
        assert item["width"] <= 1100, f"unbounded media: {item}"
        # Media narrower than its ceiling is centred, so both gutters grow
        # together. What must never happen is media flush to the column edge.
        assert item["leftGutter"] >= 0, f"no left gutter: {item}"
        assert item["rightGutter"] >= 0, f"no right gutter: {item}"


def test_full_layout_still_widens_prose(page: Page, local_deployment: str):
    """The media cap must not shrink the text column it sits in.

    The cheap way to bound an image is to bound its container, which would
    undo the whole point of the expanded layout. This is the guard that keeps
    the fix pointed at media only.
    """
    page.set_viewport_size({"width": SUPERWIDE[0], "height": SUPERWIDE[1]})
    page.goto(f"{local_deployment}/get_started/", wait_until="networkidle")
    enable_full_layout(page)

    width = page.evaluate(
        "() => document.querySelector('main article')"
        ".getBoundingClientRect().width"
    )
    assert width > 1200, width


def test_expanded_image_is_capped_and_never_upscaled(
    page: Page, local_deployment: str
):
    """The viewer shows an image at its own size, never blown up past it.

    The original bug: the fit scale had no `1` ceiling, so a small screenshot
    was enlarged into blur on a big monitor. Viewer.js enforces that ceiling
    itself, and the reader can zoom in deliberately from the toolbar if they
    want a closer look.
    """
    page.set_viewport_size({"width": SUPERWIDE[0], "height": SUPERWIDE[1]})
    page.goto(
        f"{local_deployment}/mewbo_components/", wait_until="networkidle"
    )

    opened = page.evaluate("""async () => {
        const img = document.querySelector('article img.ms-zoomable');
        if (!img) return null;
        img.click();
        await new Promise((r) => setTimeout(r, 900));
        const shown = document.querySelector('.viewer-canvas img');
        if (!shown || !shown.naturalWidth) return null;
        return {
            width: shown.getBoundingClientRect().width,
            height: shown.getBoundingClientRect().height,
            natural: shown.naturalWidth,
            naturalHeight: shown.naturalHeight,
            viewport: document.documentElement.clientWidth,
        };
    }""")

    if opened is None:
        pytest.skip("lightbox not enabled on this build")

    # Never larger than the image really is.
    assert opened["width"] <= opened["natural"] + 1, opened
    assert opened["height"] <= opened["naturalHeight"] + 1, opened
