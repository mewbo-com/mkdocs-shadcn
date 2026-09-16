"""The header's right-hand cluster is one row of matching controls.

Two things went wrong here and both were visible at a glance:

The shortcut hint rendered as a single flat monospace box reading "Ctrl K" —
not the site's keycaps, no separation between the two keys, and a different
typeface from every other shortcut on the site.

The version dropdowns rendered as two unrelated controls. There are two of
them (mike's `<select>` and the Mewbo branch switcher), one was unstyled and
clipped its own text, one carried a redundant "Version" label, and they
disagreed on height with each other and with the icon buttons beside them.
"""

from playwright.sync_api import Page

# Both dropdowns are injected rather than built: the demo site publishes no
# versions.json, so neither switcher ever appears in it. What is under test is
# the CSS contract they share, which does not care who created the nodes.
INJECT_SWITCHERS = """() => {
  const row = document.querySelector('header .ml-auto');

  const mike = document.createElement('select');
  mike.id = 'version-selector';
  for (const v of ['main (latest)', 'v2']) {
    const option = document.createElement('option');
    option.textContent = v;
    mike.appendChild(option);
  }
  row.insertBefore(mike, row.firstChild);

  const wrap = document.createElement('div');
  wrap.id = 'version-switcher';
  wrap.className = 'ms-header-select';
  const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  icon.classList.add('ms-header-select__icon');
  icon.setAttribute('viewBox', '0 0 24 24');
  const select = document.createElement('select');
  for (const v of ['1.27.0', '1.26.2']) {
    const option = document.createElement('option');
    option.textContent = v;
    select.appendChild(option);
  }
  wrap.appendChild(icon);
  wrap.appendChild(select);
  row.insertBefore(wrap, row.firstChild);
}"""


def test_search_hint_is_two_separate_keycaps(
    page: Page, local_deployment: str
):
    """`Ctrl` and `K` are two caps, styled like every other shortcut."""
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(local_deployment + "/", wait_until="networkidle")

    measured = page.evaluate("""() => {
        const group = document.querySelector('.mewbo-kbd');
        if (!group) return null;
        const caps = [...group.querySelectorAll('kbd')];
        return {
            count: caps.length,
            labels: caps.map((c) => c.textContent.trim()),
            // A keycap is built from a border plus a drop shadow; a flat box
            // has neither. This is what separates the two designs.
            shadows: caps.map((c) => getComputedStyle(c).boxShadow),
            fontSize: parseFloat(getComputedStyle(group).fontSize),
        };
    }""")

    assert measured is not None, "no shortcut hint in the header"
    assert measured["count"] == 2, measured
    assert measured["labels"][1] == "K", measured
    assert measured["labels"][0] in ("Ctrl", "⌘"), measured
    for shadow in measured["shadows"]:
        assert shadow not in ("none", ""), measured
    # Small enough not to compete with the placeholder beside it.
    assert measured["fontSize"] <= 14, measured


def test_header_controls_share_one_height_and_baseline(
    page: Page, local_deployment: str
):
    """Every control in the right-hand cluster lines up with its neighbours."""
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(local_deployment + "/", wait_until="networkidle")
    page.evaluate(INJECT_SWITCHERS)
    page.wait_for_timeout(200)

    controls = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('header .ml-auto > *').forEach((el) => {
            const box = el.getBoundingClientRect();
            if (box.height === 0) return;
            out.push({
                el: el.id || el.tagName,
                height: Math.round(box.height),
                top: Math.round(box.top),
            });
        });
        return out;
    }""")

    assert len(controls) >= 3, controls
    heights = {c["height"] for c in controls}
    tops = {c["top"] for c in controls}
    assert len(heights) == 1, f"controls disagree on height: {controls}"
    assert len(tops) == 1, f"controls are not on one baseline: {controls}"


def test_version_dropdown_does_not_clip_its_own_text(
    page: Page, local_deployment: str
):
    """A native select sizes its box from font metrics and cut the text off."""
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(local_deployment + "/", wait_until="networkidle")
    page.evaluate(INJECT_SWITCHERS)
    page.wait_for_timeout(200)

    box = page.evaluate("""() => {
        const el = document.querySelector('#version-selector');
        const style = getComputedStyle(el);
        return {
            height: el.getBoundingClientRect().height,
            lineHeight: parseFloat(style.lineHeight),
            fontSize: parseFloat(style.fontSize),
        };
    }""")

    # The line box must fit inside the control, or glyph descenders are cut.
    assert box["lineHeight"] <= box["height"] + 0.5, box
    assert box["height"] - box["fontSize"] >= 8, box


def test_only_essential_controls_survive_on_a_phone(
    page: Page, local_deployment: str
):
    """A 390px header carries search, the repo link and the theme toggle.

    Version and branch pickers are desktop affordances; on a phone they only
    compete for a row that has no space to give.
    """
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(local_deployment + "/", wait_until="networkidle")
    page.evaluate(INJECT_SWITCHERS)
    page.wait_for_timeout(200)

    visible = page.evaluate("""() => {
        const out = [];
        document.querySelectorAll('header .ml-auto > *').forEach((el) => {
            if (el.getBoundingClientRect().height > 0) {
                out.push(el.id || el.tagName);
            }
        });
        return out;
    }""")

    assert "version-selector" not in visible, visible
    assert "version-switcher" not in visible, visible
    assert len(visible) <= 3, visible
