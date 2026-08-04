import json
from collections import defaultdict
from typing import Dict, List, Union
from urllib.parse import urlparse, urlunparse

from conftest import BASE
from playwright.sync_api import ConsoleMessage, Error, Page

BrowserError = Union[ConsoleMessage, Error]


def format_errors(errors_by_page: Dict[str, List[BrowserError]]) -> str:
    if len(errors_by_page) == 0:
        return ""
    out = ""
    for url, errs in errors_by_page.items():
        out += f"😱 {url} ({len(errs)}):\n"
        for e in errs:
            if isinstance(e, ConsoleMessage):
                out += json.dumps(
                    {
                        "text": e.text,
                        "url": e.location["url"] if e.location else "",
                        "lineNumber": e.location["lineNumber"]
                        if e.location
                        else None,
                        "columnNumber": e.location["columnNumber"]
                        if e.location
                        else None,
                    },
                    indent=2,
                )
            elif isinstance(e, Error):
                out += json.dumps(
                    {
                        "name": e.name,
                        "message": e.message,
                        "stack": e.stack.replace("\n", "").replace("  ", " ")
                        if e.stack
                        else "",
                        "args": e.args,
                    },
                    indent=2,
                )
            out += "\n"
    return out


# fixtures: see https://playwright.dev/python/docs/test-runners#fixtures
def test_all_pages_no_browser_errors(page: Page, local_deployment: str):
    visited = set()
    to_visit = [local_deployment + "/"]
    errors_by_page: Dict[str, List[BrowserError]] = defaultdict(list)

    base_url = urlparse(BASE)
    errors: List[BrowserError] = []

    def _is_third_party_fetch(msg: ConsoleMessage) -> bool:
        """A failed request to somebody else's server is not a theme defect.

        The header's stargazer count calls api.github.com, which answers 403
        the moment the host is rate limited. That surfaces as a console error
        and failed this whole crawl for a reason no change to this repo can
        fix — which is worse than useless, because a suite that is red for
        environmental reasons is a suite people stop reading.

        Only requests to origins the site does not own are excused, and only
        resource-load failures: a JavaScript error thrown BY a third-party
        script still fails, because that one we chose to ship.
        """
        text = msg.text or ""
        if "Failed to load resource" not in text:
            return False
        location = getattr(msg, "location", None) or {}
        origin = location.get("url", "") if isinstance(location, dict) else ""
        return bool(origin) and base_url.netloc not in origin

    def console_error_handler(msg: ConsoleMessage):
        if msg.type == "error" and not _is_third_party_fetch(msg):
            errors.append(msg)

    def page_error_handler(err: Error):
        errors.append(err)

    page.on(
        "console",
        console_error_handler,
    )
    page.on("pageerror", page_error_handler)

    while to_visit:
        url = to_visit.pop()
        if url in visited:
            continue

        visited.add(url)

        errors.clear()
        page.goto(url, wait_until="networkidle")

        if errors:
            errors_by_page[url].extend(errors)

        # Collect internal links
        anchors = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => e.href)"
        )
        for href in anchors:
            normalized = urlparse(href)
            if normalized.scheme not in ["http", "https"]:
                continue
            normalized = normalized._replace(fragment="")
            if normalized.path.endswith("/"):
                normalized = normalized._replace(
                    path=normalized.path + "index.html"
                )
            link = urlunparse(normalized)
            if normalized.netloc == base_url.netloc and link not in visited:
                to_visit.append(link)

    assert not errors_by_page, format_errors(errors_by_page)


def test_tables_wrap_no_horizontal_scroll(page: Page, local_deployment: str):
    """Regression test: table cells must NOT have white-space:nowrap.

    Root cause of the original bug: the theme applied `whitespace-nowrap`
    to every `th` and `td`, which — combined with the
    `.table-wrapper { overflow-x: auto }` wrapper — caused wide tables to
    produce a horizontal scrollbar instead of wrapping their content.

    This test will FAIL if any upstream merge reintroduces that style.
    """
    page.set_viewport_size({"width": 800, "height": 1000})
    page.goto(
        BASE + "/table_wrap_regression/",
        wait_until="networkidle",
    )

    cells = page.locator("article table td, article table th")
    cell_count = cells.count()
    assert cell_count > 0, (
        "No table cells found — check that table_wrap_regression.md is "
        "built and served at /table_wrap_regression/"
    )

    for i in range(cell_count):
        cell = cells.nth(i)
        ws = page.evaluate(
            "el => getComputedStyle(el).whiteSpace",
            cell.element_handle(),
        )
        assert ws != "nowrap", (
            f"Cell {i} has white-space:nowrap — "
            "reintroduction of the whitespace-nowrap regression"
        )

    wrappers = page.locator(".table-wrapper")
    for i in range(wrappers.count()):
        wrapper = wrappers.nth(i)
        sw = page.evaluate("el => el.scrollWidth", wrapper.element_handle())
        cw = page.evaluate("el => el.clientWidth", wrapper.element_handle())
        assert sw <= cw + 1, (
            f"table overflows: scrollWidth={sw} clientWidth={cw}"
        )


def test_alternate_style_tabs_switch(page: Page, local_deployment: str):
    """Modern pymdownx `alternate_style: true` tabs must show/hide panels.

    The theme originally styled only the legacy adjacency markup; the alternate
    markup (`.tabbed-alternate` with `.tabbed-labels` + `.tabbed-block`) had no
    rules, so panels rendered permanently hidden. This asserts the positional
    CSS added in tailwind/tabs.css actually toggles the active panel.
    """
    page.goto(BASE + "/mewbo_components/", wait_until="networkidle")

    tabset = page.locator(".tabbed-alternate").first
    blocks = tabset.locator(".tabbed-content > .tabbed-block")
    labels = tabset.locator(".tabbed-labels > label")
    assert blocks.count() >= 3, "fixture should have 3 alternate-style tabs"

    # First panel open by default, the others hidden.
    assert blocks.nth(0).is_visible()
    assert not blocks.nth(1).is_visible()
    assert not blocks.nth(2).is_visible()

    # Clicking the second label reveals panel 2 and hides panel 1.
    labels.nth(1).click()
    assert blocks.nth(1).is_visible()
    assert not blocks.nth(0).is_visible()

    # And the third.
    labels.nth(2).click()
    assert blocks.nth(2).is_visible()
    assert not blocks.nth(1).is_visible()


def test_carousel_mounts(page: Page, local_deployment: str):
    """The carousel feature must initialise Swiper on `.ms-shots` blocks.

    Guards the theme.carousel wiring (Swiper CDN + js/carousel.js) and the
    class-based initialiser: carousel.js sets data-mounted and Swiper adds the
    `swiper-initialized` class to the root once it boots.
    """
    page.goto(BASE + "/mewbo_components/", wait_until="networkidle")

    # carousel.js polls briefly for the CDN-loaded Swiper, then mounts.
    page.wait_for_selector(".ms-shots[data-mounted='1']", timeout=8000)
    carousel = page.locator(".ms-shots").first
    cls = carousel.get_attribute("class") or ""
    assert "swiper-initialized" in cls, (
        f"carousel did not initialise; class={cls!r}"
    )


def test_header_tabs_rail_renders(page: Page, local_deployment: str):
    """theme.header_tabs renders the rail with exactly one active tab.

    Guards the optional second header row: the configured labels render in
    order, exactly one item carries aria-current="page" (the build-time
    Jinja resolution in templates/header_tabs.html), and the active item's
    computed color equals the theme accent (--primary-text) — i.e. the .ms-*

    This asserted `--primary` until light-mode contrast was measured: the fill
    value lands at 2.97:1 on the cream rail, under the 3:1 floor for a
    non-text indicator. The active tab is still the clay accent, now via the
    text-tuned variant. In dark the two are the same value, so this assertion
    is unchanged there.

    The point of the check is that the .ms-* kit in mewbo.css actually
    applies.
    """
    page.goto(BASE + "/", wait_until="networkidle")

    rail = page.locator(".ms-header-tabs")
    assert rail.count() == 1, "rail should render when header_tabs is set"

    labels = page.locator(
        ".ms-header-tabs__item > span:not(.ms-header-tabs__icon)"
    ).all_inner_texts()
    assert labels == ["Documentation", "Guides", "App Demo"], labels

    active = page.locator('.ms-header-tabs__item[aria-current="page"]')
    assert active.count() == 1, "exactly one tab must be aria-current"
    assert "Documentation" in active.inner_text(), (
        "the root tab must be active on the docs root"
    )

    got, expected = page.evaluate(
        """el => {
            const probe = document.createElement('div');
            probe.style.color = 'var(--primary-text)';
            document.body.appendChild(probe);
            const expected = getComputedStyle(probe).color;
            probe.remove();
            return [getComputedStyle(el).color, expected];
        }""",
        active.element_handle(),
    )
    assert got == expected, (
        f"active tab color {got!r} != resolved --primary-text {expected!r}"
    )


def test_header_tabs_grow_header_height(page: Page, local_deployment: str):
    """With tabs on, --header-height covers BOTH rows; the top row is pinned.

    The docs layout derives the sidebar/ToC sticky offsets from
    --header-height, so when the rail is enabled body.ms-has-header-tabs
    must raise the token by the rail's 2.5rem while .mewbo-header__row is
    pinned back to the original spacing*14. Otherwise content slides under
    the taller header.
    """
    page.goto(BASE + "/", wait_until="networkidle")

    m = page.evaluate(
        """() => {
            const probe = document.createElement('div');
            probe.style.height = 'var(--header-height)';
            document.body.appendChild(probe);
            const token = probe.getBoundingClientRect().height;
            probe.remove();
            const px = (el) => el.getBoundingClientRect().height;
            const sidebar =
                document.querySelector('[data-slot="sidebar"]');
            return {
                token,
                header: px(document.querySelector('.mewbo-header')),
                row: px(document.querySelector('.mewbo-header__row')),
                rail: px(document.querySelector('.ms-header-tabs')),
                sidebarTop: sidebar
                    ? parseFloat(getComputedStyle(sidebar).top)
                    : null,
            };
        }"""
    )

    base = 14 * 4  # calc(var(--spacing) * 14) at the default 16px root
    rail = 2.5 * 16
    assert abs(m["row"] - base) < 1, (
        f"top row must stay pinned at {base}px, got {m['row']}"
    )
    assert abs(m["token"] - (base + rail)) < 1, (
        f"--header-height must grow to {base + rail}px, got {m['token']}"
    )
    assert m["token"] > base, "--header-height must be larger with tabs on"
    # Real rendered header ≈ token (±borders): nothing slides under it.
    assert abs(m["header"] - m["token"]) <= 3, (
        f"header renders {m['header']}px but --header-height says "
        f"{m['token']}px — sticky offsets would drift"
    )
    assert m["sidebarTop"] is not None and m["sidebarTop"] >= m["header"], (
        f"sidebar sticky top {m['sidebarTop']} < header {m['header']} — "
        "the sidebar would slide under the header"
    )


def test_app_template_full_bleed(page: Page, local_deployment: str):
    """`template: app.html` keeps the header (+ rail) and drops the grid.

    The page must render NO sidebar, ToC, article wrapper, prev/next or
    footer, while the brand header and tab rail stay; its single
    .ms-app-main slot must span the viewport below the header (the page's
    own full-height div fills it completely).
    """
    page.goto(BASE + "/app_demo/", wait_until="networkidle")

    assert page.locator(".mewbo-header").count() == 1
    assert page.locator(".ms-header-tabs").count() == 1
    active = page.locator('.ms-header-tabs__item[aria-current="page"]')
    assert active.count() == 1
    assert "App Demo" in active.inner_text()

    for absent in (
        '[data-slot="sidebar"]',
        '[data-slot="docs"]',
        "article",
        "footer",
        ".mewbo-toc",
    ):
        assert page.locator(absent).count() == 0, (
            f"app.html must not render {absent}"
        )

    m = page.evaluate(
        """() => {
            const main = document.querySelector('.ms-app-main');
            const fill = document.getElementById('app-demo-fill');
            const probe = document.createElement('div');
            probe.style.height = 'var(--header-height)';
            document.body.appendChild(probe);
            const token = probe.getBoundingClientRect().height;
            probe.remove();
            return {
                main: main.getBoundingClientRect().height,
                fill: fill.getBoundingClientRect().height,
                viewport: window.innerHeight,
                token,
            };
        }"""
    )
    assert abs(m["main"] - (m["viewport"] - m["token"])) < 2, (
        f"app slot {m['main']}px should fill viewport {m['viewport']}px "
        f"minus header {m['token']}px"
    )
    assert abs(m["fill"] - m["main"]) < 2, (
        "the page's 100%-height div must fill the whole app slot"
    )


def _sidebar_link_paths(page: Page) -> List[str]:
    """Pathnames of every left-sidebar nav link on the current page."""
    return page.locator(
        '[data-slot="sidebar"] a[data-slot="sidebar-menu-button"]'
    ).evaluate_all("els => els.map(e => new URL(e.href).pathname)")


def _sidebar_group_labels(page: Page) -> List[str]:
    """Section group-label texts in the left sidebar on the current page."""
    return page.locator(
        '[data-slot="sidebar"] [data-sidebar="group-label"]'
    ).all_inner_texts()


def test_scoped_sidebar_shows_only_claimed_section(page: Page, local_deployment: str):
    """A header_tabs `section:` claim scopes the sidebar to that section.

    The Guides tab declares `section: Guides`. On a page inside the Guides
    section the left sidebar must list ONLY the Guides children and drop the
    rest of the nav (Extensions/Plugins/Reference).
    """
    page.goto(BASE + "/guides/alpha/", wait_until="networkidle")

    paths = _sidebar_link_paths(page)
    assert paths, "the scoped sidebar should still render the guides links"
    assert all(p.startswith("/guides/") for p in paths), paths
    assert not any(
        p.startswith(("/extensions/", "/plugins/", "/reference/"))
        for p in paths
    ), paths
    # The Guides children are flat pages, so no sub-section group-labels leak.
    labels = _sidebar_group_labels(page)
    assert "Extensions" not in labels and "Plugins" not in labels, labels


def test_scoped_sidebar_root_excludes_claimed_sections(page: Page, local_deployment: str):
    """On a root-tab page the sidebar shows the full nav minus claimed sections.

    The docs root is not inside any claimed section, so the sidebar keeps the
    unclaimed sections (Extensions/Reference) but drops the claimed Guides
    section entirely.
    """
    page.goto(BASE + "/", wait_until="networkidle")

    labels = _sidebar_group_labels(page)
    assert "Guides" not in labels, labels
    assert "Extensions" in labels, (
        f"unclaimed sections must still render on root pages: {labels}"
    )

    paths = _sidebar_link_paths(page)
    assert not any(p.startswith("/guides/") for p in paths), paths


def test_header_tabs_match_prefix_activates_tab(page: Page, local_deployment: str):
    """A `match:` prefix marks the tab active outside its own url subtree.

    `/reference/` is not the Guides tab's url (`guides/`) but is listed in its
    `match:` prefixes, so the Guides tab carries aria-current on reference
    pages while every other tab stays inactive.
    """
    page.goto(BASE + "/reference/api/", wait_until="networkidle")

    active = page.locator('.ms-header-tabs__item[aria-current="page"]')
    assert active.count() == 1, "exactly one tab must be aria-current"
    assert "Guides" in active.inner_text(), (
        f"the match: prefix must activate the Guides tab: {active.inner_text()!r}"
    )


def test_footer_docs_shortlist(page: Page, local_deployment: str):
    """theme.footer.docs shortlists the footer Documentation column.

    The fixture declares docs: [Get started, Guides, Reference]; the
    auto-derived column (a dozen entries without the shortlist) must
    render exactly those three, in nav order (templates/footer.html).
    """
    page.goto(BASE + "/", wait_until="networkidle")

    links = page.locator(
        'nav[aria-label="Documentation links"] li'
    ).all_inner_texts()
    assert [t.strip() for t in links] == ["Get started", "Guides", "Reference"], links


def test_tabs_beyond_eight_render(page: Page, local_deployment: str):
    """Regression test: a tab set larger than eight must still render.

    `alternate_style` emits every radio first, then one label row, then one
    content block, so a radio is never adjacent to its own label or panel and
    the CSS has to pair them positionally by index. That pairing is written
    out by hand, and the enumeration originally stopped at eight.

    The failure mode is what makes this worth a test: a ninth tab matched no
    rule at all, so clicking it selected NOTHING — a blank panel, no console
    error, nothing in the build to point at it. Silent, and invisible to
    every other check in this suite.

    The fixture carries ten tabs. Each one must show exactly one panel.
    """
    page.goto(BASE + "/tabs_regression/", wait_until="networkidle")

    labels = page.locator(".tabbed-set .tabbed-labels > label")
    count = labels.count()
    assert count >= 10, (
        f"expected the 10-tab fixture, found {count} labels — check that "
        "tabs_regression.md is built and served at /tabs_regression/"
    )

    for i in range(count):
        labels.nth(i).click()
        visible = page.evaluate(
            """() => [...document.querySelectorAll(
                 '.tabbed-set .tabbed-content > .tabbed-block')]
                 .filter(b => getComputedStyle(b).display !== 'none').length"""
        )
        assert visible == 1, (
            f"tab {i + 1} of {count} shows {visible} panels, expected 1 — "
            "the positional enumeration in tailwind/tabs.css does not reach "
            "this tab"
        )


def test_code_block_features(page: Page, local_deployment: str):
    """The markup `pymdownx.highlight` emits must actually be styled.

    The theme was styled for `codehilite`'s markup while the docs site it was
    built for had moved to `pymdownx.highlight`, so several features rendered
    bare: a fence title was a run of unstyled text, and the line-number table
    was caught by the PROSE table rules (and by the table mixin's wrapper),
    which gave it full width and pushed the code away from the left edge.

    None of that raises an error, so only a rendered assertion catches it.
    """
    page.goto(BASE + "/code_blocks/", wait_until="networkidle")

    # A fence title renders as a header strip, not bare text.
    filename = page.locator("div.codehilite > .filename").first
    assert filename.count() > 0, "no .filename — check pymdownx.highlight is on"
    assert (
        page.evaluate(
            "el => getComputedStyle(el).display", filename.element_handle()
        )
        == "block"
    ), "fence title is not styled as a block"

    # The line-number table is pygments', not prose: it must NOT be wrapped by
    # the table mixin, and must not stretch to the block's full width.
    assert page.evaluate(
        """() => !document.querySelector(
             '.table-wrapper > table.codehilitetable')"""
    ), "the code line-number table was wrapped as if it were a prose table"

    geom = page.evaluate(
        """() => {
             const t = document.querySelector('table.codehilitetable');
             if (!t) return null;
             const block = t.closest('div.codehilite').getBoundingClientRect();
             const code = t.querySelector('td.code').getBoundingClientRect();
             return {table: t.getBoundingClientRect().width,
                     block: block.width, codeLeft: code.left - block.left};
           }"""
    )
    assert geom, "no line-number table — check linenums is exercised"
    assert geom["table"] < geom["block"], (
        f"line-number table stretched to the block width "
        f"({geom['table']} vs {geom['block']}) — prose table CSS is leaking "
        "into code blocks"
    )
    assert geom["codeLeft"] < 80, (
        f"code starts {geom['codeLeft']}px from the block's left edge — the "
        "gutter is being stretched"
    )

    # Inline highlighting must stay inline, not take a block's top margin.
    inline = page.locator("p code.codehilite").first
    assert inline.count() > 0, "no inline highlight — check pymdownx.inlinehilite"
    style = page.evaluate(
        """el => ({display: getComputedStyle(el).display,
                  marginTop: getComputedStyle(el).marginTop})""",
        inline.element_handle(),
    )
    assert style["display"] == "inline", (
        "inline highlighted code is not inline — a bare `.codehilite` "
        "selector is catching it with block rules"
    )
    assert style["marginTop"] == "0px", (
        f"inline highlighted code has margin-top {style['marginTop']}"
    )


def test_abbr_tooltips_are_marked(page: Page, local_deployment: str):
    """`abbr` gives a native tooltip; the theme must SHOW that one exists."""
    page.goto(BASE + "/tooltips/", wait_until="networkidle")
    abbr = page.locator("article abbr[title]").first
    assert abbr.count() > 0, "no <abbr> — check the abbr extension is enabled"
    style = page.evaluate(
        """el => ({deco: getComputedStyle(el).textDecorationStyle,
                  cursor: getComputedStyle(el).cursor})""",
        abbr.element_handle(),
    )
    assert style["deco"] == "dotted", "abbreviation carries no underline cue"
    assert style["cursor"] == "help"


def test_sortable_tables(page: Page, local_deployment: str):
    """Clicking a header must reorder rows, and only PROSE tables attach.

    A pygments line-number gutter is a <table> too; sorting one would
    scramble a code block, so the attach step excludes it structurally.
    """
    page.goto(BASE + "/table_wrap_regression/", wait_until="networkidle")
    table = page.locator("article table.is-sortable").first
    assert table.count() > 0, "no sortable table — check theme.sortable_tables"

    result = page.evaluate(
        """() => {
             const t = document.querySelector('article table.is-sortable');
             const col = r => r.cells[0].textContent.trim();
             const before = [...t.tBodies[0].rows].map(col);
             t.tHead.rows[0].cells[0].click();
             const after = [...t.tBodies[0].rows].map(col);
             return {before, after,
                     sorted: JSON.stringify(after) ===
                             JSON.stringify([...after].sort())};
           }"""
    )
    assert result["before"] != result["after"], "clicking the header did nothing"
    assert result["sorted"], f"rows are not in order: {result['after'][:3]}"

    assert page.evaluate(
        "() => !document.querySelector('table.codehilitetable.is-sortable')"
    ), "a code block's line-number table was made sortable"


def test_videos_prepared_for_viewport_autoplay(page: Page, local_deployment: str):
    """The theme must normalise videos so viewport autoplay is possible.

    Playback itself depends on the browser's autoplay policy, which differs
    between a headless run and a real one, so this asserts the part the theme
    actually controls: a clip is muted, inline and looping, and a clip that
    opted out is left completely alone.
    """
    page.goto(BASE + "/video/", wait_until="networkidle")
    page.wait_for_timeout(500)

    state = page.evaluate(
        """() => [...document.querySelectorAll('article video')].map(v => ({
             optedOut: v.hasAttribute('data-no-autoplay'),
             muted: v.muted, loop: v.loop,
             playsinline: v.hasAttribute('playsinline'),
           }))"""
    )
    assert len(state) >= 2, "expected the video fixture's two clips"

    managed = [v for v in state if not v["optedOut"]]
    assert managed, "no managed clip in the fixture"
    for v in managed:
        assert v["muted"], "a clip the theme starts must be muted to be allowed to"
        assert v["playsinline"], "without playsinline iOS goes fullscreen instead"
        assert v["loop"], "short illustration clips loop"

    opted = [v for v in state if v["optedOut"]]
    assert opted and not opted[0]["muted"], (
        "data-no-autoplay must leave a clip entirely alone, including its audio"
    )


def test_keyboard_keys_and_header_chrome(page: Page, local_deployment: str):
    """Shortcuts render as <kbd>, and the header's three planes stay distinct.

    `tailwind/kbd.css` styled <kbd> long before anything emitted it, so
    authors wrote shortcuts as prose or inline code. `pymdownx.keys` is what
    produces the markup.

    The header, the tab rail and the page previously shared one surface, so
    they read as a single plane; the rail must sit on its own.
    """
    page.goto(BASE + "/keyboard/", wait_until="networkidle")

    keys = page.locator("article kbd")
    assert keys.count() > 0, "no <kbd> — check pymdownx.keys is enabled"
    assert page.locator("article kbd.key-command").count() > 0, (
        "no macOS Command key — cross-platform modifiers must render"
    )
    assert page.locator("article kbd.key-windows").count() > 0, (
        "no Windows key — cross-platform modifiers must render"
    )

    planes = page.evaluate(
        """() => {
             const cs = e => e ? getComputedStyle(e) : null;
             const hdr = document.querySelector('.mewbo-header');
             const rail = document.querySelector('.ms-header-tabs');
             const pill = document.querySelector('.mewbo-nav-search-pill');
             if (!hdr || !rail || !pill) return null;
             return {header: cs(hdr).backgroundColor,
                     rail: cs(rail).backgroundColor,
                     railShadow: cs(rail).boxShadow,
                     pill: cs(pill).backgroundColor,
                     pillShadow: cs(pill).boxShadow};
           }"""
    )
    assert planes, "header, rail or search pill missing"
    assert planes["rail"] != planes["header"], (
        "the tab rail shares the header's surface, so the two read as one plane"
    )
    assert planes["railShadow"] != "none", "the rail has no depth against the page"
    assert planes["pill"] != planes["header"], (
        "the search pill is not filled, so it reads as an outline not a field"
    )
    assert planes["pillShadow"] != "none"


def test_sidebar_renders_once(page: Page, local_deployment: str):
    """The left sidebar must render exactly once.

    An upstream sync left two `sidebar-content` blocks in main.html — the
    fork's solid-divider version and upstream's older gradient one — each
    including sidebar.html, so the whole nav rendered twice, one below the
    other. Conflict resolution produced valid HTML and a clean build, so
    nothing failed; only looking at the page showed it.
    """
    page.goto(BASE + "/", wait_until="networkidle")
    counts = page.evaluate(
        """() => ({
             content: document.querySelectorAll('[data-sidebar="content"]').length,
             slot: document.querySelectorAll('[data-slot="sidebar"]').length,
           })"""
    )
    assert counts["content"] == 1, (
        f"{counts['content']} sidebar content blocks — the nav is duplicated"
    )
    assert counts["slot"] == 1, f"{counts['slot']} sidebar slots"


def test_diagram_fit_is_stable_across_opens(page: Page, local_deployment: str):
    """Opening a diagram must always fit it the same way.

    The fit divided the painted rect by `viewer.scale` to recover the natural
    size. That assumes the transform on screen is the one that variable
    names, and on open the wrapper still carried the PREVIOUS diagram's
    scale — so the fit came out as `correct / previous` and COMPOUNDED:
    measured 3.50, then 0.49, then clamped at the 6x ceiling, then 0.28.

    Reset restores the stored fit, so once that value was wrong every reset
    was wrong with it. Natural size now comes from the SVG's own declared
    width and viewBox, which no transform can distort.
    """
    page.goto(BASE + "/mermaid/", wait_until="networkidle")
    page.wait_for_timeout(2000)

    def open_and_scale(index: int) -> float:
        page.evaluate(
            f"document.querySelectorAll('figure.ms-mermaid')[{index}].click()"
        )
        page.wait_for_timeout(600)
        scale = page.evaluate(
            """() => {
                 const inner = document.querySelector(
                   'dialog.ms-diagram-viewer .ms-diagram-viewer__inner');
                 const m = /scale\\(([\\d.]+)\\)/.exec(inner.style.transform || '');
                 return m ? parseFloat(m[1]) : 0;
               }"""
        )
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        return scale

    first = open_and_scale(0)
    assert first > 0, "diagram did not open, or no transform was applied"

    # Alternating opens are what surfaced the compounding.
    open_and_scale(1)
    again = open_and_scale(0)
    assert abs(again - first) < 0.01, (
        f"same diagram fitted at {first} then {again} — the fit depends on "
        "whatever was opened before it"
    )

    # Reset must return to that same fit, not to a drifted one.
    page.evaluate("document.querySelectorAll('figure.ms-mermaid')[0].click()")
    page.wait_for_timeout(600)
    for _ in range(4):
        page.evaluate("document.querySelector('[data-act=in]').click()")
    page.wait_for_timeout(250)
    page.evaluate("document.querySelector('[data-act=reset]').click()")
    page.wait_for_timeout(350)
    after_reset = page.evaluate(
        """() => {
             const inner = document.querySelector(
               'dialog.ms-diagram-viewer .ms-diagram-viewer__inner');
             const m = /scale\\(([\\d.]+)\\)/.exec(inner.style.transform || '');
             return m ? parseFloat(m[1]) : 0;
           }"""
    )
    page.keyboard.press("Escape")
    assert abs(after_reset - first) < 0.01, (
        f"reset went to {after_reset}, not the fit {first}"
    )
