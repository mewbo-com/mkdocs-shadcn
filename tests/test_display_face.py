"""Editorial reading/display faces must not leak into code or API symbols."""

import pytest
from playwright.sync_api import Page

DISPLAY = "Instrument Serif"
BODY = "Newsreader"
SANS = "Geist"
MONO = "Geist Mono"


@pytest.fixture
def fixture_page(page: Page, local_deployment: str) -> Page:
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(
        local_deployment + "/display_face_regression/",
        wait_until="networkidle",
    )
    page.evaluate("document.fonts.ready")
    return page


@pytest.mark.parametrize(
    "selector,family",
    [
        ("article #page-header h1", DISPLAY),
        ("article .typography h2", DISPLAY),
        ("article .typography h3", DISPLAY),
        (".ms-card__title", DISPLAY),
        (".ms-step__title", DISPLAY),
        (".ms-hero h1", DISPLAY),
        (".mewbo-brand__name", DISPLAY),
        (".mewbo-footer__name", DISPLAY),
        (".ms-header-tabs__item", DISPLAY),
        ("article .typography p", BODY),
        (".ms-card__body", BODY),
        (".ms-hero__lede", BODY),
        ('[data-sidebar="content"] a', BODY),
        (".mewbo-toc__link", BODY),
        ("article .typography h4", SANS),
        ("article .typography h5", SANS),
        (".ms-hero__eyebrow", SANS),
        (".mewbo-brand__docs", SANS),
        ("article .typography h2 code", MONO),
    ],
)
def test_type_roles(fixture_page: Page, selector: str, family: str):
    actual = fixture_page.locator(selector).first.evaluate("""el =>
      getComputedStyle(el).fontFamily.split(',')[0].replace(/["']/g,'').trim()
    """)
    assert actual == family, (selector, actual)


@pytest.mark.parametrize(
    "selector",
    [
        "article .typography h2",
        ".ms-hero h1",
        ".ms-card__title",
        ".ms-step__title",
        ".mewbo-brand__name",
        ".ms-header-tabs__item",
    ],
)
def test_display_uses_its_real_weight(fixture_page: Page, selector: str):
    weight = fixture_page.locator(selector).first.evaluate(
        "el=>getComputedStyle(el).fontWeight"
    )
    assert weight == "400", (selector, weight)


def test_hero_stays_larger_than_section_headings(fixture_page: Page):
    metrics = fixture_page.evaluate("""() => {
      const size=s=>parseFloat(getComputedStyle(document.querySelector(s)).fontSize);
      return {hero:size('.ms-hero h1'), section:size('article .typography h2')};
    }""")
    assert metrics["hero"] > metrics["section"], metrics


def test_mkdocstrings_symbols_opt_out(page: Page, local_deployment: str):
    page.goto(
        local_deployment + "/plugins/mkdocstrings/", wait_until="networkidle"
    )
    family = page.locator(".doc h3").first.evaluate(
        "el=>getComputedStyle(el).fontFamily"
    )
    assert SANS in family, family


def test_editorial_tokens_do_not_change_technical_stacks(fixture_page: Page):
    tokens = fixture_page.evaluate("""() => {
      const s=getComputedStyle(document.documentElement);
      return Object.fromEntries(['body','display','sans','serif','mono'].map(n=>
        [n,s.getPropertyValue('--font-'+n).trim()]));
    }""")
    assert DISPLAY in tokens["display"]
    assert BODY in tokens["body"]
    assert DISPLAY not in tokens["serif"]
    assert SANS in tokens["sans"]
    assert MONO in tokens["mono"]


def test_editorial_faces_are_loaded_locally(fixture_page: Page):
    loaded = fixture_page.evaluate("""async () => {
      await document.fonts.ready;
      return {faces:[...document.fonts].filter(f=>f.status==='loaded')
          .map(f=>f.family.replace(/["']/g,'')),
        external:performance.getEntriesByType('resource').map(r=>r.name)
          .filter(u=>/fonts\\.(googleapis|gstatic)\\.com/.test(u))};
    }""")
    assert DISPLAY in loaded["faces"], loaded
    assert BODY in loaded["faces"], loaded
    assert not loaded["external"], loaded
