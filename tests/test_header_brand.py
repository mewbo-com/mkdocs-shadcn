"""Rendered regressions for the responsive header brand cluster."""

import pytest
from playwright.sync_api import Page


@pytest.mark.parametrize("width", [1024, 1280, 2560])
def test_desktop_brand_has_a_large_name_and_docs_badge(
    page: Page, local_deployment: str, width: int
):
    """Desktop branding stays prominent without taking space from search."""
    page.set_viewport_size({"width": width, "height": 900})
    page.goto(local_deployment + "/", wait_until="networkidle")

    brand = page.locator(".mewbo-brand")
    glyph = brand.locator(".mewbo-brand__glyph")
    name = brand.locator(".mewbo-brand__name")
    badge = brand.locator(".mewbo-brand__docs")

    geometry = page.evaluate("""() => {
        const box = selector => {
            const rect = document.querySelector(selector).getBoundingClientRect();
            return { left: rect.left, right: rect.right, width: rect.width };
        };
        return {
            header: box('.mewbo-header__row'),
            brand: box('.mewbo-brand'),
            search: box('#mewbo-search-trigger'),
            utility: box('.mewbo-header__row > div:last-child'),
            scrollWidth: document.documentElement.scrollWidth,
            viewportWidth: innerWidth,
        };
    }""")

    assert (
        glyph.evaluate("element => element.getBoundingClientRect().width")
        >= 28
    )
    assert (
        name.evaluate(
            "element => parseFloat(getComputedStyle(element).fontSize)"
        )
        >= 21
    )
    assert badge.inner_text() == "Docs"
    assert (
        badge.evaluate("element => getComputedStyle(element).borderStyle")
        == "solid"
    )
    assert geometry["search"]["width"] >= 180, geometry
    assert geometry["brand"]["right"] <= geometry["search"]["left"], geometry
    assert geometry["search"]["right"] <= geometry["utility"]["left"], geometry
    assert geometry["scrollWidth"] <= geometry["viewportWidth"], geometry


def test_mobile_hides_the_desktop_brand_without_horizontal_overflow(
    page: Page, local_deployment: str
):
    """The larger desktop identity cannot crowd the mobile header."""
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(local_deployment + "/", wait_until="networkidle")

    assert not page.locator(".mewbo-brand").is_visible()
    assert page.locator("#menu-button").is_visible()
    assert page.locator("#mewbo-mobile-search").is_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
