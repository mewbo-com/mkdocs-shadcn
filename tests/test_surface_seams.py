"""Paper must fill the rail to the viewport edge and meet the footer."""

from __future__ import annotations

import base64
import colorsys
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from playwright.sync_api import Page


def patch_rgb(page: Page, x: float, y: float) -> list[float]:
    png = base64.b64encode(
        page.screenshot(
            clip={"x": x, "y": y, "width": 8, "height": 8},
            animations="disabled",
        )
    ).decode()
    return page.evaluate(
        """async png => {
      const image=new Image();image.src='data:image/png;base64,'+png;await image.decode();
      const canvas=document.createElement('canvas');canvas.width=canvas.height=8;
      const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0);
      const data=ctx.getImageData(0,0,8,8).data, sum=[0,0,0];
      for(let i=0;i<data.length;i+=4) for(let c=0;c<3;c++) sum[c]+=data[i+c]/64;
      return sum;
    }""",
        png,
    )


@pytest.mark.parametrize("width", [1024, 1440, 1920, 2560])
@pytest.mark.parametrize("layout", ["fixed", "full"])
@pytest.mark.parametrize("dark", [False, True])
def test_sidebar_stock_has_no_viewport_or_footer_seams(
    page: Page, local_deployment: str, width: int, layout: str, dark: bool
):
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(
        local_deployment + "/mewbo_components/", wait_until="networkidle"
    )
    page.evaluate(
        """({layout,dark}) => {
      const root=document.documentElement;
      root.classList.toggle('dark',dark);
      root.classList.toggle('layout-fixed',layout==='fixed');
      root.classList.toggle('layout-full',layout==='full');
      root.style.scrollBehavior='auto';
      document.querySelectorAll('.swiper').forEach(e=>e.swiper?.autoplay.stop());
      scrollTo({top:0,behavior:'instant'});
    }""",
        {"layout": layout, "dark": dark},
    )
    sidebar = page.locator('[data-slot="sidebar"]').bounding_box()
    header = page.locator(".mewbo-header").bounding_box()
    x = sidebar["x"] + 12
    y = header["y"] + header["height"] + 96
    stock = patch_rgb(page, x, y)
    samples = [
        patch_rgb(page, 4, y),
        patch_rgb(page, sidebar["x"] + sidebar["width"] - 18, y),
    ]
    page.evaluate(
        "scrollTo({top:document.documentElement.scrollHeight,behavior:'instant'})"
    )
    footer = page.locator(".mewbo-footer").bounding_box()
    samples.extend(
        [
            patch_rgb(page, 4, footer["y"] - 12),
            patch_rgb(page, x, footer["y"] - 12),
        ]
    )
    for sample in samples:
        assert max(abs(a - b) for a, b in zip(stock, sample)) <= 3, (
            width,
            layout,
            dark,
            stock,
            samples,
        )
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_table_wrappers_do_not_paint_scroll_covers(
    page: Page, local_deployment: str
):
    page.goto(
        local_deployment + "/table_wrap_regression/", wait_until="networkidle"
    )
    wrappers = page.locator("article .table-wrapper")
    assert wrappers.count()
    for wrapper in wrappers.all():
        paint = wrapper.evaluate(
            "el=>{const c=getComputedStyle(el);return [c.backgroundImage,c.boxShadow,c.overflowX]}"
        )
        assert paint == ["none", "none", "auto"], paint


def test_tab_labels_have_no_artificial_shading(
    page: Page, local_deployment: str
):
    page.goto(
        local_deployment + "/mewbo_components/", wait_until="networkidle"
    )
    for labels in page.locator(".tabbed-labels").all():
        assert labels.evaluate("el=>getComputedStyle(el).boxShadow") == "none"
        assert (
            labels.evaluate("el=>getComputedStyle(el).backgroundImage")
            == "none"
        )


@pytest.mark.parametrize("dark", [False, True])
def test_bright_ink_white_stock_and_saturated_accent(
    page: Page, local_deployment: str, dark: bool
):
    page.goto(local_deployment + "/", wait_until="networkidle")
    colours = page.evaluate(
        """dark=>{
      document.documentElement.classList.toggle('dark',dark);
      const root=getComputedStyle(document.documentElement);
      const canvas=document.createElement('canvas');canvas.width=canvas.height=1;
      const ctx=canvas.getContext('2d');
      const rgb=colour=>{ctx.fillStyle=colour;ctx.fillRect(0,0,1,1);return [...ctx.getImageData(0,0,1,1).data].slice(0,3)};
      return {white:rgb(root.getPropertyValue(dark?'--foreground':'--card')),
        prose:rgb(getComputedStyle(document.querySelector('article')).color),
        accent:rgb(root.getPropertyValue('--primary'))};
    }""",
        dark,
    )
    assert min(colours["white"]) >= 250, colours
    if dark:
        assert min(colours["prose"]) >= 250, colours
    assert (
        colorsys.rgb_to_hsv(*(v / 255 for v in colours["accent"]))[1] >= 0.65
    ), colours


def test_paper_alpha_is_reduced_by_a_quarter():
    svg = ET.parse(
        Path(__file__).resolve().parents[1] / "shadcn/img/paper.svg"
    )
    alpha = svg.find(".//{http://www.w3.org/2000/svg}feFuncA")
    assert float(alpha.attrib["slope"]) == pytest.approx(0.052 * 0.75)
