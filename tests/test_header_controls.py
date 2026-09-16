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

import pytest
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


# Resolves any CSS colour -- `oklab()`, `color-mix()`, alpha -- to the sRGB
# the screen actually shows, by painting it over a known base. `getComputedStyle`
# hands back the authored function verbatim, which no contrast maths can read.
MEASURE_HINT = """() => {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 1;
  const ctx = canvas.getContext('2d', {willReadFrequently: true});
  const paint = (css, under) => {
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = under; ctx.fillRect(0, 0, 1, 1);
    ctx.fillStyle = css; ctx.fillRect(0, 0, 1, 1);
    const d = ctx.getImageData(0, 0, 1, 1).data;
    return [d[0], d[1], d[2]];
  };
  const hex = (c) =>
    '#' + c.map((v) => Math.round(v).toString(16).padStart(2, '0')).join('');
  const luminance = (c) => {
    const f = (v) => {
      v /= 255;
      return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
    };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
  };
  const contrast = (a, b) => {
    const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
  };

  const pill = document.querySelector('.mewbo-nav-search-pill');
  const cap = document.querySelector('.mewbo-kbd kbd');
  const group = cap.parentElement;
  const placeholder = pill.querySelector('span');
  const header = pill.closest('header');
  const style = getComputedStyle(cap);

  // The group's opacity multiplies every colour inside it onto the pill, so
  // it has to be folded in or the numbers describe a cap nobody can see.
  const alpha = parseFloat(getComputedStyle(group).opacity);
  const over = (c, base) => c.map((v, i) => v * alpha + base[i] * (1 - alpha));

  const headerFill = paint(getComputedStyle(header).backgroundColor, '#ffffff');
  const pillFill = paint(getComputedStyle(pill).backgroundColor, hex(headerFill));
  const face = over(paint(style.backgroundColor, hex(pillFill)), pillFill);
  const label = over(paint(style.color, hex(face)), face);
  const hint = paint(getComputedStyle(placeholder).color, hex(pillFill));

  return {
    pillFill: hex(pillFill),
    capFace: hex(face),
    capLabel: hex(label),
    placeholder: hex(hint),
    labelContrast: contrast(label, pillFill),
    placeholderContrast: contrast(hint, pillFill),
    faceContrast: contrast(face, pillFill),
  };
}"""


def _measure_hint(page: Page, dark: bool) -> dict:
    """Switch theme, let the style recalc land, then measure.

    Toggling `.dark` and reading in the same evaluate returns a half-updated
    picture -- the cap resolves against the new palette while the pill behind
    it still reports the old fill, which silently compares colours that never
    coexist on screen. The separate call plus a rendered frame is what makes
    both sides of every ratio belong to the same theme.
    """
    page.evaluate(
        "dark => document.documentElement.classList.toggle('dark', dark)", dark
    )
    page.wait_for_timeout(120)
    return page.evaluate(MEASURE_HINT)


@pytest.mark.parametrize("dark", [False, True])
def test_search_keycaps_stay_quieter_than_the_placeholder(
    page: Page, local_deployment: str, dark: bool
):
    """The Ctrl/K hint recedes behind the "Search..." text it accompanies.

    The hint is an affordance, not content. A reader scanning the header should
    land on the word "Search" first; the caps are there to be found once they
    are already looking. Pinning the cap label BELOW the placeholder's own
    contrast is what encodes that ordering -- an absolute threshold would drift
    the moment the palette moves, because "subtle" is a statement about the
    neighbour, not about an absolute.
    """
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(local_deployment + "/", wait_until="networkidle")
    measured = _measure_hint(page, dark)

    # Quieter than its neighbour, and by a real margin rather than a rounding.
    assert measured["labelContrast"] < measured["placeholderContrast"], (
        measured
    )
    # Still legible: AA for incidental UI text is 3:1.
    assert measured["labelContrast"] >= 3.0, measured


@pytest.mark.parametrize("dark", [False, True])
def test_search_keycaps_read_as_caps_not_as_paint(
    page: Page, local_deployment: str, dark: bool
):
    """Toning the hint down must not erase the cap it is drawn on.

    The face is meant to be a whisper against the field, but a face that
    resolves to exactly the field is not a keycap at all -- it is the label
    floating with a stray border. This is the floor that stops a subtler
    palette from being achieved by deleting the thing.
    """
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(local_deployment + "/", wait_until="networkidle")
    measured = _measure_hint(page, dark)

    assert measured["capFace"] != measured["pillFill"], measured
    # Present but never a second button: a hard ceiling on how loud it gets.
    assert 1.02 <= measured["faceContrast"] <= 2.0, measured


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
