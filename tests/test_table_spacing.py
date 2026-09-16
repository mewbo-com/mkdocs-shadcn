"""Table cells that wrap are set with paragraph leading, not grid leading.

The theme's table rules descend from shadcn/ui's app data-table, where every
cell is one line and tight leading is correct. These tables wrap by design
(see `tailwind/table.css`), so a long cell is a small paragraph rendered at
data-grid leading — and a cell carrying inline `code` was worse, because a
chip's vertical padding eats into the gap and consecutive lines of chips very
nearly touched.

Measured from the rendered line boxes rather than the declaration: what the
reader sees is the distance between one wrapped line and the next, and it is
the chips, not the cell, that close that distance.
"""

import pytest
from playwright.sync_api import Page

FIXTURE = "/table_wrap_regression/"


@pytest.mark.parametrize("width", [390, 1440])
def test_table_cells_have_prose_leading(
    page: Page, local_deployment: str, width: int
):
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(local_deployment + FIXTURE, wait_until="networkidle")

    # The two-column table, not the five-column one above it: five wide
    # columns is a stress fixture that wraps every cell to one or two words,
    # which is not the shape this leading is for.
    metrics = page.locator("article table").last.evaluate(
        """async table => {
          await document.fonts.ready;
          // Found by content rather than index, so reordering the fixture
          // does not silently point this at a one-line cell.
          const cell = [...table.querySelectorAll('tbody tr')]
            .find(r => r.cells[0].textContent.trim() === 'Windows')
            .cells[1];
          const style = getComputedStyle(cell);
          // Line boxes, top to bottom: consecutive tops are the leading a
          // reader actually perceives between wrapped lines. A chip sits a
          // few px proud of the text it shares a line with (its padding makes
          // it taller), so the rects have to be CLUSTERED into lines — taking
          // distinct tops verbatim reports a 1px "line step" within one line
          // and makes the assertion below meaningless.
          const range = document.createRange();
          range.selectNodeContents(cell);
          const tops = [...range.getClientRects()]
            .map(r => r.top)
            .sort((a, b) => a - b);
          const lines = [];
          for (const top of tops) {
            if (!lines.length || top - lines[lines.length - 1] > 8) {
              lines.push(top);
            }
          }
          const steps = lines.slice(1).map((t, i) => Math.round(t - lines[i]));
          return {
            fontSize: parseFloat(style.fontSize),
            lineHeight: parseFloat(style.lineHeight),
            whiteSpace: style.whiteSpace,
            hasCode: !!cell.querySelector('code'),
            lines: lines.length,
            minStep: steps.length ? Math.min(...steps) : null,
          };
        }"""
    )

    assert metrics["hasCode"] and metrics["lines"] >= 2, (
        "the fixture is not the wrapped prose-plus-chips cell this measures — "
        f"code={metrics['hasCode']} lines={metrics['lines']}"
    )

    # `leading-relaxed`, the same step `article p` uses. It was 1.43 — the
    # shadcn data-table default, tighter than any body copy on the page.
    ratio = metrics["lineHeight"] / metrics["fontSize"]
    assert ratio >= 1.6, (
        f"table cells are set at {ratio:.2f} leading — tighter than the prose "
        "around them, so wrapped cells read as a dense block"
    )

    # The defect was never the declared value alone; it was the gap left after
    # a code chip's padding. Assert the rendered step.
    assert metrics["minStep"] >= 20, (
        f"wrapped lines in a cell with code chips are only "
        f"{metrics['minStep']}px apart"
    )

    # The whole point of the leading is that cells wrap. Guard it here too, so
    # this test fails rather than passing vacuously if nowrap ever returns.
    assert metrics["whiteSpace"] == "normal", (
        f"cell white-space is {metrics['whiteSpace']}, not normal"
    )
