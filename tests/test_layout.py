"""Browser regressions for the documentation-width layout toggle."""

from playwright.sync_api import Page, expect


def test_full_layout_expands_only_page_article_and_persists(
    page: Page, local_deployment: str
):
    """The ultrawide toggle gives page prose the available center width.

    This fails if the base article's fixed 42rem maximum remains active in
    ``layout-full``, or if its localStorage state stops applying on reload.
    """
    page.set_viewport_size({"width": 2560, "height": 1440})
    page.goto(local_deployment + "/", wait_until="networkidle")

    article = page.locator("main article")
    fixed_width = article.evaluate(
        "element => element.getBoundingClientRect().width"
    )
    assert 640 <= fixed_width <= 700, fixed_width

    page.get_by_title("Toggle layout").click()
    expect(page.locator("html")).to_have_class("layout-full")
    full = article.evaluate("""element => {
        const box = element.getBoundingClientRect();
        return {
            width: box.width,
            leftGutter: box.x,
            rightGutter: innerWidth - box.right,
            scrollWidth: document.documentElement.scrollWidth,
            viewportWidth: innerWidth,
        };
    }""")

    assert full["width"] > 1400, full
    assert full["leftGutter"] >= 16, full
    assert full["rightGutter"] >= 16, full
    assert full["scrollWidth"] <= full["viewportWidth"], full

    page.reload(wait_until="networkidle")
    expect(page.locator("html")).to_have_class("layout-full")
    persisted_width = article.evaluate(
        "element => element.getBoundingClientRect().width"
    )
    assert persisted_width > 1400, persisted_width

    page.get_by_title("Toggle layout").click()
    expect(page.locator("html")).to_have_class("layout-fixed")
    restored_width = article.evaluate(
        "element => element.getBoundingClientRect().width"
    )
    assert 640 <= restored_width <= 700, restored_width


def test_full_layout_leaves_mobile_article_width_unchanged(
    page: Page, local_deployment: str
):
    """The desktop-only full layout must not alter mobile document gutters."""
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(local_deployment + "/", wait_until="networkidle")

    article = page.locator("main article")
    before = article.evaluate(
        "element => element.getBoundingClientRect().width"
    )
    page.evaluate("""() => {
        document.documentElement.classList.remove('layout-fixed');
        document.documentElement.classList.add('layout-full');
    }""")
    after = article.evaluate(
        "element => element.getBoundingClientRect().width"
    )

    assert after == before
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
