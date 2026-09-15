"""Rendered geometry guards for diagram previews and the expanded viewer."""

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture
def diagrams(page: Page, local_deployment: str):
    page.set_viewport_size({"width": 2560, "height": 1440})
    page.goto(local_deployment + "/mermaid/", wait_until="networkidle")
    expect(page.locator(".ms-mermaid--pending")).to_have_count(0)
    expect(page.locator(".ms-mermaid--error")).to_have_count(0)
    expect(page.locator(".ms-mermaid__stage > svg")).to_have_count(7)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    yield page.locator("figure.ms-mermaid")
    assert not errors, errors


def assert_viewer_fits(page: Page):
    page.wait_for_function("""() => {
      const svg = document.querySelector('.ms-diagram-viewer__inner > svg');
      const stage = document.querySelector('.ms-diagram-viewer__stage');
      if (!svg || !stage) return false;
      const s = svg.getBoundingClientRect(), r = stage.getBoundingClientRect();
      return s.width > 0 && s.height > 0 &&
        Math.abs(s.x + s.width / 2 - r.x - r.width / 2) < 2 &&
        Math.abs(s.y + s.height / 2 - r.y - r.height / 2) < 2 &&
        s.width <= r.width && s.height <= r.height &&
        Math.max(s.width / r.width, s.height / r.height) > 0.9;
    }""")


def test_viewer_uses_large_display(page: Page, diagrams):
    diagrams.nth(0).locator("button").click()
    box = page.locator("dialog.ms-diagram-viewer").bounding_box()
    assert box["width"] > 2300, box
    assert box["height"] > 1250, box
    assert_viewer_fits(page)
    page.set_viewport_size({"width": 1280, "height": 800})
    assert_viewer_fits(page)


@pytest.mark.parametrize("index", [0, 1])
def test_theme_change_keeps_active_diagram_fitted(
    page: Page, diagrams, index: int
):
    diagrams.nth(index).locator("button").click()
    assert_viewer_fits(page)
    page.evaluate("document.documentElement.classList.toggle('dark')")
    # Wait for the new SVG, not merely the old correctly fitted geometry.
    page.wait_for_function("""() => document.querySelector(
      '.ms-diagram-viewer__inner > svg style').textContent.includes('#f8f8f6')
    """)
    svg_text = page.locator(".ms-diagram-viewer__inner").inner_text()
    label = ["Author writes a fence", "Ingest the repository"][index]
    assert label in svg_text, svg_text
    assert_viewer_fits(page)


def test_viewer_fits_svg_with_different_declared_width(page: Page, diagrams):
    page.evaluate("""() => {
      const source = 'flowchart LR; A-->B';
      const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100%" '
        + 'style="max-width: 800px" viewBox="0 0 400 200">'
        + '<rect width="400" height="200" fill="red" /></svg>';
      svgCache.set(`light|${source}`, svg);
      const card = buildCard(source, svg, 99);
      document.querySelector('article').append(card);
      openViewer(card);
    }""")
    assert_viewer_fits(page)


def test_layout_change_does_not_reset_viewer(page: Page, diagrams):
    diagrams.nth(1).locator("button").click()
    assert_viewer_fits(page)
    page.get_by_role("button", name="Zoom in", exact=True).click()
    inner = page.locator(".ms-diagram-viewer__inner")
    before = inner.inner_html()
    transform = inner.get_attribute("style")
    page.evaluate("document.documentElement.classList.toggle('layout-full')")
    page.wait_for_timeout(300)
    assert inner.inner_html() == before
    assert inner.get_attribute("style") == transform


@pytest.mark.parametrize("width", [390, 2560, 3840])
def test_previews_fill_column_without_unreadable_shrinking(
    page: Page, diagrams, width: int
):
    page.set_viewport_size({"width": width, "height": 1440})
    page.wait_for_function("""() => [...document.querySelectorAll(
      '.ms-mermaid__stage > svg')].every(svg =>
        svg.getBoundingClientRect().width >= svg.parentElement.clientWidth - 2)
    """)
    metrics = page.locator(".ms-mermaid__stage > svg").evaluate_all("""svgs =>
      svgs.map(svg => ({
        width: svg.getBoundingClientRect().width,
        natural: svg.viewBox.baseVal.width,
        available: svg.parentElement.clientWidth,
        overflow: getComputedStyle(svg.parentElement).overflowX,
      }))
    """)
    for size in metrics:
        assert size["width"] >= size["available"] - 2, size
        assert size["width"] / size["natural"] >= 0.74, size
        assert size["overflow"] == "hidden", size
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
