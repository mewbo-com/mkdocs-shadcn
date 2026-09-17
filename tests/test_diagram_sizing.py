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


def test_wide_display_widens_the_diagram_column(page: Page, diagrams):
    """A diagram is not prose, so it does not take the prose measure.

    `article` is capped at `max-w-2xl` (672px) because a long line of TEXT is
    hard to read. A diagram has no line length, and applying the prose measure
    to one meant a 1026px flowchart was squeezed into 672px on EVERY display,
    where the legibility floor (`min-width: natural * 0.75`) cropped it —
    measured 132px cut off a six-node phase chart on a 2560px monitor, while
    ~1900px of that monitor went to margin.

    WHAT THIS DOES NOT CLAIM: that every diagram fits. The bleed is bounded by
    the sticky ToC rail and the sidebar, which own the space beside the column
    — measured headroom is 132px per side at 1536px+, so the column reaches
    ~888px and a diagram wider than that is still cropped. The demo site's
    widest is 1373px and remains so. Fixing THAT needs the rails to yield,
    which is a layout decision beyond this rule.

    So this pins the two things the rule does guarantee: the column is
    genuinely wider than the prose measure on a wide display, and widening it
    costs no horizontal page scroll.
    """
    page.set_viewport_size({"width": 2560, "height": 1440})
    page.wait_for_timeout(300)
    metrics = page.locator("figure.ms-mermaid").evaluate_all("""figs =>
      figs.map(f => {
        const stage = f.querySelector('.ms-mermaid__stage');
        const article = f.closest('article');
        return {
          id: f.dataset.diagramId,
          natural: f.querySelector('svg').viewBox.baseVal.width,
          stage: stage.getBoundingClientRect().width,
          prose: article.getBoundingClientRect().width,
        };
      })
    """)
    assert metrics, "no diagrams on the page"
    # Only diagrams that WANT more room take it. A narrow one is capped at its
    # own natural width rather than stretched across the bleed, so the rule is
    # proven by the diagrams wide enough to need it.
    wants_room = [m for m in metrics if m["natural"] > m["prose"]]
    assert wants_room, (
        "no diagram on the fixture page is wider than the prose column, so "
        "this test cannot prove the wide-screen rule applies"
    )
    for size in wants_room:
        assert size["stage"] > size["prose"], (
            f"{size['id']} is a {size['natural']:.0f}px diagram held to a "
            f"{size['stage']:.0f}px stage inside a {size['prose']:.0f}px "
            f"prose column — the wide-screen rule that lets a diagram exceed "
            f"the text measure is not applying"
        )
    # The escape must not cost a horizontal scrollbar on the page itself.
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_diagram_column_clears_the_sidebar_and_toc_rails(page: Page, diagrams):
    """The widened figure must not slide under the chrome beside it.

    The bleed is negative margin, so it is capable of running straight under
    the sticky ToC rail — and the rail is a later stacking context, so it wins
    the hit test: an earlier 13rem bleed overlapped it by 76px per side and the
    rail silently swallowed every click on the expand button. The diagram was
    wider and less usable, which is the wrong trade.
    """
    page.set_viewport_size({"width": 2560, "height": 1440})
    page.wait_for_timeout(300)
    bounds = page.evaluate("""() => {
      const fig = document.querySelector('figure.ms-mermaid');
      const rail = [...document.querySelectorAll('div')].find(
        d => d.className.includes('sticky') && d.className.includes('w-72'));
      const sidebar = document.querySelector('[data-slot="sidebar"]');
      const f = fig.getBoundingClientRect();
      return {
        figLeft: f.left, figRight: f.right,
        railLeft: rail ? rail.getBoundingClientRect().left : Infinity,
        sidebarRight: sidebar ? sidebar.getBoundingClientRect().right : 0,
      };
    }""")
    assert bounds["figRight"] <= bounds["railLeft"], (
        f"the diagram figure reaches {bounds['figRight']:.0f}px but the ToC "
        f"rail starts at {bounds['railLeft']:.0f}px — it is running under the "
        f"rail, which will intercept clicks on the expand button"
    )
    assert bounds["figLeft"] >= bounds["sidebarRight"], (
        f"the diagram figure starts at {bounds['figLeft']:.0f}px but the "
        f"sidebar ends at {bounds['sidebarRight']:.0f}px — it is running "
        f"under the sidebar"
    )

    # The expand button must actually be clickable, not merely un-overlapped.
    diagrams.first.locator(".ms-mermaid__expand").click(timeout=5000)
    expect(page.locator("dialog.ms-diagram-viewer")).to_be_visible()


def test_viewer_never_fits_against_a_collapsed_stage(page: Page, diagrams):
    """The open fit must survive running before the dialog has a size.

    A closed `<dialog>` is `display: none`, so every rectangle inside it
    measures 0x0. `recomputeFit` used to run in that state on any paint that
    resolved before `showModal()` — which is exactly what a warm `svgCache`
    produces — and computed `(0 - FIT_MARGIN) / naturalW`, a NEGATIVE scale
    that the clamp turned into MIN_SCALE. The diagram then opened at 0.2 in the
    corner of an empty stage and looked like it had failed to render.

    It is a race, so it reproduced intermittently and never on a cold cache,
    which is how it survived the previous fix. This drives the failing state
    directly rather than waiting to get unlucky: fit while collapsed, then
    confirm the diagram is still correctly fitted once the stage has a size.
    """
    page.set_viewport_size({"width": 2560, "height": 1440})
    figure = diagrams.first
    figure.locator(".ms-mermaid__expand").click()
    assert_viewer_fits(page)

    # Collapse the stage and force the fit path. The guard must decline.
    scale_while_closed = page.evaluate("""() => {
      const dlg = document.querySelector('dialog.ms-diagram-viewer');
      dlg.close();
      window.dispatchEvent(new Event('resize'));
      const inner = document.querySelector('.ms-diagram-viewer__inner');
      const m = getComputedStyle(inner).transform.match(/matrix\\(([-\\d.]+)/);
      return m ? parseFloat(m[1]) : null;
    }""")
    assert (
        scale_while_closed is None or abs(scale_while_closed - 0.2) > 0.01
    ), (
        "the viewer fitted against a 0x0 stage and clamped to MIN_SCALE — "
        "a collapsed stage must be declined, not measured"
    )

    # Reopening must land a correct fit, proving the bail-out is not a dead end.
    figure.locator(".ms-mermaid__expand").click()
    assert_viewer_fits(page)
