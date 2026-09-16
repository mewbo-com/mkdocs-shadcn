"""Find what makes the page itself scroll sideways at a narrow width.

Not a test — a diagnostic you point at a running site to get the list of
culprits. `pytest tests/test_responsive_overflow.py` is the regression gate;
this is what you run while fixing one, because it names the offending element
and the chain of ancestors that failed to contain it, which an assertion
cannot.

    uv run python internal/overflow_probe.py --port 8091 --width 320
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from typing import Any

from playwright.sync_api import sync_playwright

# Reports every element wider than its containing block, then walks up from
# each to find the first ancestor that *should* have contained it. Runs in the
# page because a round trip per element is far too slow over CDP.
PROBE = """
() => {
  const docWidth = document.documentElement.clientWidth;
  const out = [];
  const describe = (el) => {
    const id = el.id ? `#${el.id}` : '';
    const cls = (el.className && typeof el.className === 'string')
      ? '.' + el.className.trim().split(/\\s+/).slice(0, 3).join('.')
      : '';
    return `${el.tagName.toLowerCase()}${id}${cls}`;
  };
  // Two shapes of false positive, both by design:
  //   `.sr-only` is a 1px clipped box whose text is meant to overflow it;
  //   anything inside a scrolling ancestor is already swipeable, which is the
  //   behaviour we want for a code block and not a bug to report.
  const excused = (el) => {
    if (el.closest('.sr-only')) return true;
    let p = el.parentElement;
    while (p && p.tagName !== 'BODY') {
      const ox = getComputedStyle(p).overflowX;
      if (ox === 'auto' || ox === 'scroll') return true;
      p = p.parentElement;
    }
    return false;
  };
  document.querySelectorAll('article *').forEach((el) => {
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) return;
    if (excused(el)) return;
    // Overflowing the viewport is the symptom the reader actually feels.
    const overflowsViewport = rect.right > docWidth + 1;
    // Content wider than its own box is only a problem when the box does not
    // scroll — that is the difference between a code block you can swipe and
    // a page you cannot.
    const cs = getComputedStyle(el);
    const scrolls = cs.overflowX === 'auto' || cs.overflowX === 'scroll';
    const burstsOwnBox = el.scrollWidth > el.clientWidth + 1 && !scrolls;
    if (!overflowsViewport && !burstsOwnBox) return;
    out.push({
      el: describe(el),
      rect_right: Math.round(rect.right),
      doc_width: docWidth,
      width: Math.round(rect.width),
      scroll_width: el.scrollWidth,
      client_width: el.clientWidth,
      overflow_x: cs.overflowX,
      white_space: cs.whiteSpace,
      min_width: cs.minWidth,
      word_break: cs.wordBreak,
      overflow_wrap: cs.overflowWrap,
      ancestors: (() => {
        const chain = [];
        let p = el.parentElement;
        while (p && chain.length < 6 && p.tagName !== 'BODY') {
          const pcs = getComputedStyle(p);
          chain.push({
            el: describe(p),
            display: pcs.display,
            min_width: pcs.minWidth,
            overflow_x: pcs.overflowX,
            width: Math.round(p.getBoundingClientRect().width),
            scroll_width: p.scrollWidth,
          });
          p = p.parentElement;
        }
        return chain;
      })(),
    });
  });
  return {
    doc_scroll_width: document.documentElement.scrollWidth,
    doc_client_width: docWidth,
    body_scroll_width: document.body.scrollWidth,
    offenders: out,
  };
}
"""


class OverflowProbe:
    """Drives one browser over a list of pages and collects the offenders."""

    def __init__(self, base: str, width: int, height: int = 844) -> None:
        self.base = base.rstrip("/")
        self.width = width
        self.height = height

    def pages(self) -> list[str]:
        """Every page in the built site, read from the search index.

        The index is the only list of pages the site publishes, and it is
        already built by the time anything is worth probing.
        """
        url = f"{self.base}/search/search_index.json"
        with urllib.request.urlopen(url) as fh:  # noqa: S310 - local site
            data = json.load(fh)
        seen = []
        for doc in data.get("docs", []):
            loc = doc.get("location", "").split("#")[0]
            if loc not in seen:
                seen.append(loc)
        return seen

    def run(self, paths: list[str]) -> dict[str, Any]:
        found: dict[str, Any] = {}
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(
                viewport={"width": self.width, "height": self.height}
            )
            for path in paths:
                page.goto(f"{self.base}/{path}", wait_until="networkidle")
                result = page.evaluate(PROBE)
                if (
                    result["doc_scroll_width"] > result["doc_client_width"] + 1
                    or result["offenders"]
                ):
                    found[path or "<index>"] = result
            browser.close()
        return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--width", type=int, default=320)
    parser.add_argument("--page", action="append", default=None)
    args = parser.parse_args()

    probe = OverflowProbe(f"http://{args.host}:{args.port}", args.width)
    paths = args.page if args.page else probe.pages()
    found = probe.run(paths)

    for path, result in found.items():
        scroll = result["doc_scroll_width"]
        client = result["doc_client_width"]
        flag = "PAGE SCROLLS" if scroll > client + 1 else "contained"
        print(f"\n=== {path}  [{flag}: {scroll} vs {client}] ===")
        for off in result["offenders"][:8]:
            print(
                f"  {off['el']}  right={off['rect_right']} "
                f"w={off['width']} scrollW={off['scroll_width']} "
                f"ws={off['white_space']} ox={off['overflow_x']} "
                f"minw={off['min_width']}"
            )
            for anc in off["ancestors"][:3]:
                print(
                    f"      ^ {anc['el']}  display={anc['display']} "
                    f"minw={anc['min_width']} ox={anc['overflow_x']} "
                    f"w={anc['width']} scrollW={anc['scroll_width']}"
                )
    if not found:
        print("No overflow found.")


if __name__ == "__main__":
    main()
