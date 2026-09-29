"""Editorial prose must not resize compact UI or shrink touch targets."""

from playwright.sync_api import Browser, Page, expect


def test_search_results_keep_the_interface_face(
    page: Page, local_deployment: str
):
    page.goto(local_deployment + "/", wait_until="networkidle")
    page.locator("#mewbo-search-trigger").click()
    page.locator("#mewbo-search-input").fill("table")
    result = page.locator("#mkdocs-search-results article").first
    expect(result).to_be_visible()
    assert "Geist" in result.evaluate("el=>getComputedStyle(el).fontFamily")


def test_app_slot_keeps_interface_defaults(page: Page, local_deployment: str):
    page.goto(local_deployment + "/app_demo/", wait_until="networkidle")
    assert "Geist" in page.locator(".ms-app-main").evaluate(
        "el=>getComputedStyle(el).fontFamily"
    )


def test_mobile_navigation_targets_are_real_boxes(
    browser: Browser, local_deployment: str
):
    with browser.new_context(
        viewport={"width": 390, "height": 844}, has_touch=True
    ) as context:
        page = context.new_page()
        page.goto(local_deployment + "/", wait_until="networkidle")
        for selector in [
            "#menu-button",
            '#bottom-navigation a[data-slot="button"]',
        ]:
            for target in page.locator(selector).all():
                box = target.bounding_box()
                assert box and min(box["width"], box["height"]) >= 44, (
                    selector,
                    box,
                )
        page.locator("#menu-button").click()
        close = page.locator(".ms-mobile-nav__close")
        expect(close).to_be_visible()
        box = close.bounding_box()
        assert box and min(box["width"], box["height"]) >= 44, box
        close.click()
        expect(close).to_be_hidden()
