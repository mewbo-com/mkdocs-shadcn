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
    """The viewer takes the screen it is given — up to a readable limit.

    `95vw`/`92dvh` alone meant a 2560px monitor got a 2432px dialog and a
    diagram scaled to fill it, which is not more readable than one at 1800px,
    only wider than a pair of eyes. The max bounds in mewbo.css cap it; below
    them the proportional sizing is unchanged, which is what the 1280px leg
    still checks.
    """
    diagrams.nth(0).locator("button").click()
    box = page.locator("dialog.ms-diagram-viewer").bounding_box()
    assert box["width"] == 1800, box
    assert box["height"] == 1100, box
    assert_viewer_fits(page)
    page.set_viewport_size({"width": 1280, "height": 800})
    assert_viewer_fits(page)
    # Under the cap the dialog is still proportional to the viewport.
    small = page.locator("dialog.ms-diagram-viewer").bounding_box()
    assert 1200 < small["width"] < 1280, small


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


@pytest.mark.parametrize("width", [390, 1440, 2560, 3840])
def test_previews_fill_column_without_javascript_sizing(
    page: Page, local_deployment: str, width: int
):
    """The stylesheet alone has to lay a diagram out correctly.

    The card used to be sized entirely from JS: a ResizeObserver measured the
    stage and wrote `width`/`height` back onto the SVG. Whenever that pass did
    not land — an observer delivery dropped under load, a card revealed after
    its one measurement, a browser that never fired it — the CSS underneath was
    `justify-content: flex-start` plus `flex: none`, so mermaid's own intrinsic
    width stood and the diagram sat small in the top-left corner of a stage
    several times its width. That is invisible on a laptop, where the column is
    narrow enough that almost any diagram fills it, and obvious on a 32" display.

    So this test deliberately removes the JS lever and asserts the geometry is
    still right. It fails against a stylesheet that needs JS to be correct.
    """
    page.add_init_script(
        "window.ResizeObserver = class {"
        " observe() {} unobserve() {} disconnect() {} };"
    )
    page.set_viewport_size({"width": width, "height": 1440})
    page.goto(local_deployment + "/mermaid/", wait_until="networkidle")
    expect(page.locator(".ms-mermaid__stage > svg")).to_have_count(7)

    metrics = page.locator(".ms-mermaid__stage > svg").evaluate_all("""svgs =>
      svgs.map(svg => {
        const box = svg.getBoundingClientRect();
        const view = svg.viewBox.baseVal;
        return {
          width: box.width,
          height: box.height,
          natural: view.width,
          ratio: view.width / view.height,
          available: svg.parentElement.clientWidth,
        };
      })
    """)
    for size in metrics:
        # Fills the column, or is held back only by the legibility floor.
        assert size["width"] >= size["available"] - 2, size
        assert size["width"] / size["natural"] >= 0.74, size
        # Scaling must stay proportional: no stretched or squashed diagram.
        assert abs(size["width"] / size["height"] - size["ratio"]) < 0.05, size
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


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
