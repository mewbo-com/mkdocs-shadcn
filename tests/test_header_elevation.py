"""The complete sticky navigation stack casts a shadow over page content."""

import base64

import pytest
from playwright.sync_api import Page


@pytest.mark.parametrize("tabs", [False, True])
@pytest.mark.parametrize("dark", [False, True])
def test_header_shadow_overlays_content(
    page: Page, local_deployment: str, tabs: bool, dark: bool
):
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(
        local_deployment + "/mewbo_components/", wait_until="networkidle"
    )
    page.evaluate(
        """({tabs, dark}) => {
      document.documentElement.classList.toggle('dark', dark);
      if (!tabs) {
        document.querySelector('.ms-header-tabs').remove();
        document.body.classList.remove('ms-has-header-tabs');
      }
      document.querySelector('.ms-shots').swiper.autoplay.stop();
      document.documentElement.style.scrollBehavior = 'auto';
      scrollTo({top: 450, behavior: 'instant'});
    }""",
        {"tabs": tabs, "dark": dark},
    )
    header = page.locator(".mewbo-header")
    geometry = header.evaluate("""header => {
      const r = header.getBoundingClientRect();
      return {top: r.top, bottom: r.bottom, width: r.width,
        shadow: getComputedStyle(header).boxShadow,
        onTop: header.contains(document.elementFromPoint(700, r.bottom - 8))};
    }""")
    assert geometry["shadow"] != "none"
    assert geometry["top"] == 0
    assert geometry["onTop"]
    # Painted pixels prove the shadow survives stacking and extends beyond
    # the border. Compare the same scrolled content with only the shadow off.
    clip = {"x": 450, "y": geometry["bottom"] + 8, "width": 500, "height": 12}
    before = base64.b64encode(page.screenshot(clip=clip)).decode()
    header.evaluate("header => header.style.boxShadow = 'none'")
    after = base64.b64encode(page.screenshot(clip=clip)).decode()
    darker = page.evaluate(
        """async ([before, after]) => {
      const pixels = async data => {
        const image = new Image();
        image.src = 'data:image/png;base64,' + data;
        await image.decode();
        const canvas = document.createElement('canvas');
        canvas.width = image.width; canvas.height = image.height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(image, 0, 0);
        return ctx.getImageData(0, 0, canvas.width, canvas.height).data;
      };
      const a = await pixels(before), b = await pixels(after);
      let darker = 0;
      for (let i = 0; i < a.length; i += 4) {
        if (a[i] + a[i+1] + a[i+2] < b[i] + b[i+1] + b[i+2]) darker++;
      }
      return darker;
    }""",
        [before, after],
    )
    assert darker > 3000, (
        f"Shadow is absent or hidden behind content: {darker} pixels"
    )
    assert header.bounding_box()["y"] == 0
