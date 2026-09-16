"""Carousel controls answer every click, including impatient ones.

Swiper's `loopPreventsSliding` defaults to true, which silently discards any
`slideNext`/`slidePrev`/`slideToLoop` issued while a transition is running. With
a 300ms transition and autoplay also driving transitions, a reader clicking at a
normal pace loses most of their clicks and the carousel reads as stuck.
"""

import pytest
from playwright.sync_api import Page, expect

# Faster than the 300ms transition, which is the whole point: this is the pace
# that used to lose clicks.
CLICK_GAP_MS = 120

MOUNTED = "document.querySelector('.ms-shots').swiper"
REAL_INDEX = "() => document.querySelector('.ms-shots').swiper.realIndex"


def _open_carousel(page: Page, local_deployment: str):
    page.goto(
        local_deployment + "/mewbo_components/", wait_until="networkidle"
    )
    page.wait_for_function(MOUNTED)
    page.locator(".ms-shots").first.scroll_into_view_if_needed()
    return page.locator(".ms-shots")


@pytest.mark.parametrize(
    "control", [".swiper-button-next", ".swiper-button-prev"]
)
def test_every_arrow_click_advances_a_slide(
    page: Page, local_deployment: str, control: str
):
    """No click is swallowed, however fast they arrive."""
    carousel = _open_carousel(page, local_deployment)
    seen = [page.evaluate(REAL_INDEX)]
    for _ in range(8):
        carousel.locator(control).click()
        page.wait_for_timeout(CLICK_GAP_MS)
        seen.append(page.evaluate(REAL_INDEX))
    moved = sum(1 for a, b in zip(seen, seen[1:]) if a != b)
    assert moved == 8, f"only {moved}/8 clicks moved the carousel: {seen}"


def test_every_dot_click_selects_its_slide(page: Page, local_deployment: str):
    """A bullet always lands on the slide it points at."""
    carousel = _open_carousel(page, local_deployment)
    bullets = carousel.locator(".swiper-pagination-bullet")
    wanted = [2, 0, 1, 2, 0, 1, 2, 0]
    for index in wanted:
        bullets.nth(index).click()
        page.wait_for_timeout(CLICK_GAP_MS)
        assert page.evaluate(REAL_INDEX) == index, (
            f"dot {index} did not select slide {index}"
        )


def test_mixing_arrows_and_dots_keeps_state_consistent(
    page: Page, local_deployment: str
):
    """The active dot always agrees with the slide on screen.

    Mixing the two controls is what surfaced this: the pagination bullet and
    the visible slide drifted apart once a click had been dropped mid-loop.
    """
    carousel = _open_carousel(page, local_deployment)
    plan = [
        ".swiper-button-next",
        ".swiper-button-next",
        "bullet-0",
        ".swiper-button-prev",
        "bullet-2",
        ".swiper-button-next",
        "bullet-1",
        ".swiper-button-next",
    ]
    for step in plan:
        if step.startswith("bullet-"):
            carousel.locator(".swiper-pagination-bullet").nth(
                int(step[-1])
            ).click()
        else:
            carousel.locator(step).click()
        page.wait_for_timeout(CLICK_GAP_MS)
        agreed = page.evaluate("""() => {
          const root = document.querySelector('.ms-shots');
          const bullets = [...root.querySelectorAll('.swiper-pagination-bullet')];
          const active = bullets.findIndex(
            (b) => b.classList.contains('swiper-pagination-bullet-active'));
          return active === root.swiper.realIndex;
        }""")
        assert agreed, f"dot and slide disagree after {step}"


def test_autoplay_yields_to_the_reader(page: Page, local_deployment: str):
    """Once the reader takes control, autoplay stops competing with them."""
    carousel = _open_carousel(page, local_deployment)
    carousel.locator(".swiper-button-next").click()
    page.wait_for_timeout(CLICK_GAP_MS)
    settled = page.evaluate(REAL_INDEX)
    # Comfortably past the 4000ms autoplay delay.
    page.wait_for_timeout(5000)
    assert page.evaluate(REAL_INDEX) == settled, (
        "autoplay moved the carousel after the reader interacted"
    )


def test_carousel_survives_a_full_loop(page: Page, local_deployment: str):
    """Walking right past the end and back keeps the controls alive."""
    carousel = _open_carousel(page, local_deployment)
    for _ in range(6):
        carousel.locator(".swiper-button-next").click()
        page.wait_for_timeout(CLICK_GAP_MS)
    before = page.evaluate(REAL_INDEX)
    carousel.locator(".swiper-button-prev").click()
    page.wait_for_timeout(CLICK_GAP_MS)
    assert page.evaluate(REAL_INDEX) != before, (
        "carousel stopped responding after looping"
    )
    expect(carousel.locator(".swiper-slide-active img")).to_be_visible()
