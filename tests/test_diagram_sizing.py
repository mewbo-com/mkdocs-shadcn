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


def test_an_inflated_viewbox_is_not_believed(page: Page, diagrams):
    """The viewBox is checked against what was actually drawn, not trusted.

    On some displays mermaid emits a viewBox far larger than its own content.
    Measured on a reader's 32" monitor at `devicePixelRatio: 1.1875`: a diagram
    whose drawn content is 1027x72 was handed a viewBox of 2703x2652 — 2.6x too
    wide and 37x too tall, so 97% of the declared area was empty. Every
    consumer of that number then did correct arithmetic on a fiction, and the
    three results looked like three unrelated bugs:

      - the CSS legibility floor demanded 2027px inside a 990px stage, clipping
        519px off the diagram's left edge
      - `height: auto` made the SVG 1989px tall in a 512px stage, which is the
        tall empty card the reader sees
      - the viewer's fit computed 0.112, clamped to MIN_SCALE, and opened the
        diagram at minimum zoom

    This drives the failing state directly, because it is environmental and
    does not reproduce in a headless browser: inject the reader's exact
    viewBox, re-run the publish path, and require the theme to recover.
    """
    page.set_viewport_size({"width": 2560, "height": 1440})
    result = page.evaluate("""async () => {
      const fig = document.querySelector('figure.ms-mermaid');
      const stage = fig.querySelector('.ms-mermaid__stage');
      fig.querySelector('svg').setAttribute(
        'viewBox', '0 0 2703.5263671875 2652');
      await new Promise(r => setTimeout(r, 120));
      const svgBefore = fig.querySelector('svg').getBoundingClientRect();
      // A theme flip re-renders every card and re-runs publishNaturalSize.
      document.documentElement.classList.toggle('dark');
      await new Promise(r => setTimeout(r, 1200));
      const svg = fig.querySelector('svg');
      const s = svg.getBoundingClientRect();
      const r = stage.getBoundingClientRect();
      return {
        heightWhileInflated: svgBefore.height,
        viewBox: svg.getAttribute('viewBox'),
        overflowX: s.width - r.width,
        emptyVertical: r.height - s.height,
        svgHeight: s.height,
      };
    }""")

    assert result["heightWhileInflated"] > 600, (
        "the injected viewBox did not distort the diagram, so this test is no "
        "longer reproducing the reader's failure"
    )
    # Horizontal overflow is NOT asserted here. A diagram genuinely wider than
    # the column is still cropped by the legibility floor, which is the
    # documented trade in `test_wide_display_widens_the_diagram_column` and is
    # independent of the viewBox. What matters is that the floor is now derived
    # from the DRAWN width rather than an inflated one, which the viewBox
    # assertion below pins directly.
    assert result["viewBox"] is not None
    declared_w = float(result["viewBox"].split()[2])
    assert declared_w < 2000, (
        f"the viewBox is still {declared_w:.0f} units wide after a republish — "
        f"the inflated box was believed rather than checked against the drawn "
        f"content"
    )
    assert abs(result["emptyVertical"]) <= 2, (
        f"the stage carries {result['emptyVertical']:.0f}px of empty space "
        f"around a {result['svgHeight']:.0f}px diagram — the inflated viewBox "
        f"is still sizing the element"
    )


def test_natural_size_is_measured_after_the_card_is_in_the_document(
    page: Page, diagrams
):
    """The viewBox check is worthless if it runs before the card is attached.

    `getBBox()` is only meaningful for an element that is in the document and
    rendered. On a detached node it returns 0x0, and so does one inside a
    `display: none` subtree — both measured in Chromium, neither throws. Since
    `naturalSize` treats a zero box as "cannot measure" and falls back to the
    declared viewBox, a measurement taken one line too early does not fail
    loudly: it silently re-adopts the exact number the check exists to catch.

    That is what shipped in v1.35.0. `buildCard` called `publishNaturalSize`
    on a figure the caller had not yet inserted, so on a reader's machine a
    diagram whose content is 1027x72 published 2703px as its natural width and
    every symptom the viewBox guard was written to fix survived it.

    A HEADLESS BROWSER CANNOT SHOW THIS BY OBSERVATION. Chromium here emits a
    viewBox that already matches its content, so the fallback returns the right
    answer by luck and a wrongly-ordered build looks identical. The ordering is
    therefore asserted directly: build a card exactly as the theme does, and
    require that measuring it before insertion yields nothing while measuring
    it after insertion yields the diagram.
    """
    evidence = page.evaluate("""() => {
      const source = 'flowchart LR; A[Alpha]-->B[Beta]';
      const svg = document.querySelector('figure.ms-mermaid svg').outerHTML;
      const card = buildCard(source, svg, 900);

      // As the theme builds it: not yet in the document.
      const detached = card.querySelector('svg').getBBox();

      // As the theme now attaches it.
      const host = document.createElement('div');
      document.querySelector('article').append(host);
      host.replaceWith(card);
      const attached = card.querySelector('svg').getBBox();

      const published = (() => {
        publishNaturalSize(card);
        return parseFloat(card.querySelector('.ms-mermaid__stage')
          .style.getPropertyValue('--ms-diagram-natural')) || 0;
      })();
      card.remove();
      return {
        detached: {w: detached.width, h: detached.height},
        attached: {w: attached.width, h: attached.height},
        published,
      };
    }""")

    assert evidence["detached"]["w"] == 0, (
        f"a card measured before insertion reported "
        f"{evidence['detached']['w']:.0f}px — if that is now real, the "
        f"ordering constraint this test defends no longer applies"
    )
    assert evidence["attached"]["w"] > 0, (
        "the card measured nothing even after insertion, so this test is not "
        "exercising the path it claims to"
    )
    assert evidence["published"] > 0, (
        "publishNaturalSize produced no width for an attached card"
    )


def test_a_detached_card_cannot_be_measured(page: Page, diagrams):
    """Why the ordering above is structural rather than a style preference.

    If this ever starts reporting a real size, `getBBox()` has gained meaning
    off-document and the ordering constraint can be revisited. Until then, any
    measurement before insertion is measuring nothing.
    """
    result = page.evaluate("""() => {
      const live = document.querySelector('figure.ms-mermaid svg');
      const clone = live.cloneNode(true);
      let detached;
      try {
        const b = clone.getBBox();
        detached = {w: b.width, h: b.height};
      } catch (e) { detached = {threw: true}; }
      const attached = live.getBBox();
      return {detached, attached: {w: attached.width, h: attached.height}};
    }""")
    assert result["attached"]["w"] > 0, "the attached diagram measures nothing"
    assert result["detached"].get("threw") or result["detached"]["w"] == 0, (
        "a detached SVG now reports a real bounding box — the reason "
        "publishNaturalSize must run after insertion no longer holds"
    )


def test_viewer_opens_the_dialog_before_painting(page: Page, diagrams):
    """The viewer must be measurable at the moment it is painted.

    `openViewer` painted a cached SVG BEFORE calling `showModal()`. A closed
    `<dialog>` is `display: none`, so that paint measured a 0x0 stage and a
    `getBBox()` of 0x0: the fit declined, and `naturalSize` fell back to the
    declared viewBox. On a display where that viewBox is inflated the diagram
    then opened unfitted and outside the visible stage, and the reader had to
    scroll and zoom out to find it.

    ASSERTED AS ORDERING, not as geometry. Headless Chromium emits a sane
    viewBox and the deferred `requestAnimationFrame` fit repairs the frame
    afterwards, so the rendered result looks identical either way — a mutation
    restoring the old order still passes a geometry check. What actually broke
    is that the stage was unmeasurable when painted, so that is what is pinned.
    """
    page.set_viewport_size({"width": 2560, "height": 1440})
    evidence = page.evaluate("""() => {
      const dlg = document.querySelector('dialog.ms-diagram-viewer')
        || (() => { const d = buildViewer(); return d; })();
      const stage = dlg.querySelector('.ms-diagram-viewer__stage');
      const closed = stage.getBoundingClientRect();
      if (!dlg.open) dlg.showModal();
      const open = stage.getBoundingClientRect();
      dlg.close();
      return {closedW: closed.width, closedH: closed.height,
              openW: open.width, openH: open.height};
    }""")

    assert evidence["closedW"] == 0 and evidence["closedH"] == 0, (
        "a closed dialog now reports a real stage rectangle — the reason the "
        "viewer must open before it paints no longer holds"
    )
    assert evidence["openW"] > 0, (
        "the stage measures nothing even once open, so this test is not "
        "exercising the path it claims to"
    )

    # And the observable consequence: a cached reopen lands where the first
    # open did, which is what the reader experiences.
    figure = diagrams.first
    figure.locator(".ms-mermaid__expand").click()
    assert_viewer_fits(page)
    cold = page.evaluate(
        "() => getComputedStyle("
        "document.querySelector('.ms-diagram-viewer__inner')).transform"
    )
    page.evaluate(
        "() => document.querySelector('dialog.ms-diagram-viewer').close()"
    )
    page.wait_for_timeout(250)
    figure.locator(".ms-mermaid__expand").click()
    assert_viewer_fits(page)
    warm = page.evaluate(
        "() => getComputedStyle("
        "document.querySelector('.ms-diagram-viewer__inner')).transform"
    )
    assert cold == warm, (
        f"the cached open placed the diagram differently from the first open\n"
        f"  first (cache miss): {cold}\n"
        f"  second (cache hit): {warm}"
    )


def test_diagram_keeps_the_prose_measure(page: Page, diagrams):
    """A diagram card sits in the text column, like every other block.

    A wide-screen rule once let the figure bleed past `max-w-2xl` so a large
    diagram could be read without expanding. It was reverted: a card that
    changes width between pages — wide where a diagram happens to be large,
    narrow everywhere else — reads as a layout bug rather than as a feature,
    and the expanded viewer is where a large diagram is meant to be read.
    """
    page.set_viewport_size({"width": 2560, "height": 1440})
    page.wait_for_timeout(250)
    bounds = page.locator("figure.ms-mermaid").evaluate_all("""figs =>
      figs.map(f => {
        const a = f.closest('article').getBoundingClientRect();
        const r = f.getBoundingClientRect();
        return {id: f.dataset.diagramId,
                overhangLeft: a.left - r.left,
                overhangRight: r.right - a.right};
      })
    """)
    assert bounds, "no diagrams on the page"
    for b in bounds:
        assert b["overhangLeft"] <= 1 and b["overhangRight"] <= 1, (
            f"{b['id']} extends past the prose column "
            f"(left {b['overhangLeft']:.0f}px, right {b['overhangRight']:.0f}px)"
            f" — the reverted wide-screen bleed is back"
        )
