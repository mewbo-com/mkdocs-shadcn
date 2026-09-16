"""Keycaps look pressable, in both themes, without a bundled webfont.

These used to be drawn by a bundled font (Libertinus Keyboard) whose glyphs
carried their own outlines. That went away: 46KB of webfont for decoration,
and only some labels had glyphs — `Cmd` and the arrows fell through to a
hand-drawn box and never matched the caps beside them.

The replacement is pure CSS, so what has to be asserted is the LIGHTING. A
keycap reads as pressable because its top edge is lighter than its face and
its front edge is darker; a box with one uniform border is a badge. Nothing
about that is visible to a build, and a screenshot would not fail on it.
"""

import pytest
from playwright.sync_api import Page


# The edges are built with `color-mix()`, and the computed values come back
# as `oklab(L a b / α)`. Two dead ends before this: `rgb()` parsing does not
# fit the string, and a canvas `fillStyle` round-trip silently keeps its
# previous value for a colour it cannot parse — which reported every edge as
# black and made the comparison below trivially true.
#
# So the colours are resolved by the engine that already renders them:
# paint each one into a swatch, then read it back. `getComputedStyle` on a
# painted element returns sRGB regardless of the notation that produced it.
_RESOLVE_JS = """colors => {
  const swatch = document.createElement('span');
  swatch.style.display = 'none';
  document.body.appendChild(swatch);
  const out = colors.map(c => {
    swatch.style.color = c;
    const [r, g, b] = getComputedStyle(swatch).color.match(/[\\d.]+/g);
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  });
  swatch.remove();
  return out;
}"""


@pytest.mark.parametrize("dark", [False, True])
@pytest.mark.parametrize("width", [390, 1440])
def test_keycaps_are_lit_from_above(
    page: Page, local_deployment: str, dark: bool, width: int
):
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(local_deployment + "/keyboard/", wait_until="networkidle")
    page.evaluate(
        "dark => document.documentElement.classList.toggle('dark', dark)", dark
    )

    metrics = page.locator("article kbd.key-control").first.evaluate(
        """async key => {
          await document.fonts.ready;
          const s = getComputedStyle(key);
          // A cap's identity: its lighting colours, and its padding as a
          // RATIO of its own font-size. Caps are em-sized, so absolute px
          // legitimately differ between a 14px table cell and a 15px
          // paragraph — comparing px reports correct scaling as a mismatch.
          // The 1px border is excluded for the same reason in reverse: it
          // is deliberately NOT em-scaled (a hairline stays a hairline), so
          // its ratio drifts with context while the rule is identical.
          const sign = el => {
            const cs = getComputedStyle(el);
            const px = parseFloat(cs.fontSize);
            return [cs.borderTopColor, cs.borderBottomColor,
                    (parseFloat(cs.paddingBottom) / px).toFixed(2),
                    (parseFloat(cs.paddingTop) / px).toFixed(2)].join('|');
          };
          return {
            font: s.fontFamily,
            top: s.borderTopColor,
            side: s.borderRightColor,
            front: s.borderBottomColor,
            face: s.backgroundColor,
            shadow: s.boxShadow,
            minWidth: parseFloat(s.minWidth),
            fontSize: parseFloat(s.fontSize),
            peer: parseFloat(getComputedStyle(key.parentElement).fontSize),
            // Every cap must be styled the same way. The old font left
            // `Cmd` and the arrows with no glyph, so they fell back to a
            // hand-drawn box that did not match the caps beside them.
            //
            // Compared as a RATIO to each cap's own font-size, not as raw
            // px: caps are em-sized, so the identical rule yields different
            // absolute shadows for a cap in a 14px table cell and one in a
            // 15px paragraph. Comparing px reports that correct scaling as
            // a mismatch.
            variants: [...document.querySelectorAll(
              'article kbd.key-command, article kbd[class*=key-arrow-]')]
              .map(el => sign(el)),
            // The same signature for the reference cap, to compare against.
            signature: sign(key),
          };
        }"""
    )

    # No bundled keycap font: the cap is drawn, and the label is page type.
    assert "Libertinus" not in metrics["font"], (
        "the keycap webfont is back — caps are drawn in CSS now, in the "
        "page's own typeface"
    )

    face, top, front = page.evaluate(
        _RESOLVE_JS, [metrics["face"], metrics["top"], metrics["front"]]
    )
    # Guard the resolver itself: an all-zero read means the colours never
    # resolved, and the ordering assertions below would pass on nothing.
    assert len({face, top, front}) > 1, (
        f"every edge resolved to the same luminance ({face:.3f}) — the "
        "colour resolver is broken, not the CSS"
    )

    # The whole illusion: a light source above. Top edge brighter than the
    # face, front edge darker — in BOTH themes, which is why this is
    # parametrised rather than asserting fixed colours.
    assert top > face, (
        f"the top edge ({top:.3f}) is not lighter than the face "
        f"({face:.3f}) — the cap reads as a flat box, not a lit surface"
    )
    assert front < face, (
        f"the front edge ({front:.3f}) is not darker than the face "
        f"({face:.3f}) — there is no wall under the cap"
    )

    # A drop shadow is what sits the cap ON the page rather than in it.
    assert metrics["shadow"] != "none", "keycaps have no shadow at all"

    # `C` must not render as a sliver next to `Command`.
    assert metrics["minWidth"] >= 20, (
        f"min-width is {metrics['minWidth']}px — a one-character cap "
        "collapses to a sliver beside a long label"
    )

    # em-sized, so a cap in a table cell or a heading tracks its context.
    assert metrics["fontSize"] < metrics["peer"], (
        "keycap type does not scale with the text around it"
    )

    # Uniform treatment across labels.
    assert metrics["variants"], "no Cmd/arrow caps found on the page"
    odd = [v for v in metrics["variants"] if v != metrics["signature"]]
    assert not odd, (
        f"Cmd/arrow caps are styled differently from letter caps: {odd[0]} "
        f"against {metrics['signature']} — that was the defect the bundled "
        "font had, where those labels had no glyph and fell back to a box"
    )
