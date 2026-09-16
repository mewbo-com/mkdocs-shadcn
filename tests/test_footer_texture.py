"""The footer carries a token-derived dot lattice, faintly, behind its text.

Two failure modes, neither of which raises anything:

The texture silently not painting. It is twenty stacked radial gradients,
and the first draft asked for `circle 9.3%` — a percentage radius, which is
invalid for `circle` — so every layer was dropped at parse time and the
footer rendered exactly as before. Nothing in the build, the console or a
screenshot diff of a flat region would say so.

The texture painting too loudly. It sits behind live text, so it has to read
as a surface, not as decoration competing with the copy.
"""

import pytest
from playwright.sync_api import Page

TILE = 65


@pytest.mark.parametrize("dark", [False, True])
def test_footer_dot_lattice_is_present_and_faint(
    page: Page, local_deployment: str, dark: bool
):
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(local_deployment + "/", wait_until="networkidle")
    page.evaluate(
        "dark => document.documentElement.classList.toggle('dark', dark)", dark
    )

    metrics = page.locator(".mewbo-footer").evaluate(
        """footer => {
          const layer = getComputedStyle(footer, '::before');
          const image = layer.backgroundImage;
          return {
            // A dropped layer does not appear at all, so counting is the
            // whole test for "did the gradients survive parsing".
            layers: (image.match(/radial-gradient/g) || []).length,
            // Every layer must tile at the same size or the lattice shears.
            sizes: [...new Set(layer.backgroundSize.split(',')
              .map(s => s.trim()))],
            zIndex: layer.zIndex,
            isolation: getComputedStyle(footer).isolation,
            // Resolved through color-mix, so this is the real painted alpha.
            alphas: [1, 2, 3, 4].map(n => {
              const el = document.createElement('span');
              el.style.color = getComputedStyle(footer)
                .getPropertyValue(`--ms-footer-dot-${n}`);
              footer.appendChild(el);
              const rgb = getComputedStyle(el).color;
              el.remove();
              const m = rgb.match(/[\\d.]+/g);
              return m && m.length === 4 ? parseFloat(m[3]) : 1;
            }),
          };
        }"""
    )

    assert metrics["layers"] == 20, (
        f"the footer lattice has {metrics['layers']} of 20 gradient layers — "
        "an invalid stop (e.g. a percentage radius on `circle`) drops the "
        "whole layer at parse time and the texture silently disappears"
    )

    assert metrics["sizes"] == [f"{TILE}px {TILE}px"], (
        f"layers tile at differing sizes {metrics['sizes']} — the lattice "
        "shears instead of repeating as one tile"
    )

    # Behind the content, and in its own stacking context so the columns
    # cannot fall behind it.
    assert metrics["zIndex"] == "-1"
    assert metrics["isolation"] == "isolate"

    # Decoration under live text. The brief was "a slight effect"; at 7% the
    # dots read as a polka field rather than a texture.
    assert all(0 < a <= 0.06 for a in metrics["alphas"]), (
        f"dot alphas are {metrics['alphas']} — a texture behind body text "
        "should sit under 6%"
    )

    # Four distinct groups: the source pattern's charm is the colour scatter,
    # and collapsing them to one value gives an evenly-speckled field.
    assert len(set(metrics["alphas"])) > 1, (
        "every dot group resolved to the same value — the scatter is gone"
    )
