"""Tab strips and fenced code blocks keep a readable amount of air.

Both defects here were pure density: nothing was broken, nothing errored, and
the page was simply hard to read. A tab label sat at caption size with its
selected underline two pixels under the word, the panel started almost on top
of the strip's rule, and a fenced block was separated from the sentence
introducing it by the same gap two paragraphs get — so prose and code ran
together down the page.

Measured against the rendered geometry rather than the declarations, because
the numbers that matter are distances between boxes: a label's padding, the
panel's padding and a block's margin each come from a different rule, and any
one of them changing silently undoes the result.
"""

import pytest
from playwright.sync_api import Page

# The fixture is the last tab set on the components page: prose, a fence, then
# more prose, inside a panel — the install-instructions shape these gaps exist
# for. `pages/docs/mewbo_components.md` under "Tab and code spacing".
FIXTURE = "/mewbo_components/"


@pytest.mark.parametrize("width", [390, 1440])
def test_tab_and_code_spacing(page: Page, local_deployment: str, width: int):
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(local_deployment + FIXTURE, wait_until="networkidle")

    metrics = page.locator(".tabbed-set.tabbed-alternate").last.evaluate(
        """async set => {
          await document.fonts.ready;
          const labels = set.querySelector('.tabbed-labels');
          const label = labels.querySelector('label');
          const panel = set.querySelector('.tabbed-content > .tabbed-block');
          const code = panel.querySelector('div.codehilite');
          // The label's own box, minus the text inside it: the range is the
          // only way to ask where the glyphs actually end, which is the
          // distance a reader perceives to the underline.
          const range = document.createRange();
          range.selectNodeContents(label);
          const text = range.getBoundingClientRect();
          const box = label.getBoundingClientRect();
          const strip = labels.getBoundingClientRect();
          const first = panel.firstElementChild.getBoundingClientRect();
          const block = code.getBoundingClientRect();
          const before = code.previousElementSibling.getBoundingClientRect();
          const after = code.nextElementSibling.getBoundingClientRect();
          return {
            fontSize: parseFloat(getComputedStyle(label).fontSize),
            bodySize: parseFloat(
              getComputedStyle(panel.querySelector('p')).fontSize),
            textToUnderline: box.bottom - text.bottom,
            stripToPanel: first.top - strip.bottom,
            above: block.top - before.bottom,
            below: after.top - block.bottom,
            panelShape: [...panel.children].map(el => el.tagName),
          };
        }"""
    )

    assert metrics["panelShape"] == ["P", "DIV", "P"], (
        "the fixture is not the prose/fence/prose panel this measures — "
        f"found {metrics['panelShape']}"
    )

    # A tab label names a section, so it is set at body copy size, not the
    # step below it that it used to share with captions.
    assert metrics["fontSize"] >= metrics["bodySize"], (
        f"tab labels are {metrics['fontSize']}px against "
        f"{metrics['bodySize']}px body copy — they read as a caption"
    )

    # The selected underline has to sit clear of the descenders, not against
    # them. It was 5px, which read as an underlined word.
    assert metrics["textToUnderline"] >= 12, (
        f"only {metrics['textToUnderline']:.0f}px from the label text to its "
        "underline — the selected tab reads as underlined text"
    )

    # Below the strip's rule, before the panel's first line.
    assert metrics["stripToPanel"] >= 20, (
        f"only {metrics['stripToPanel']:.0f}px between the tab strip and the "
        "panel content"
    )

    # A framed block needs more than the paragraph flow step on both edges;
    # `--prose-flow` is 24px, so anything at or under it is the old defect.
    for edge in ("above", "below"):
        assert metrics[edge] > 24, (
            f"a fenced code block has only {metrics[edge]:.0f}px {edge} it — "
            "prose and code run together at the body flow step"
        )
