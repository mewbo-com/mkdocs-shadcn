"""Copy and build metadata work without guessing repository or page paths."""

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import Page, expect

ROOT = Path(__file__).parent.parent
MARKDOWN = '# TUI\n\n"quoted" & <tag>\n```python\nprint(1)\n```\n'


def copy_markup():
    env = Environment(loader=FileSystemLoader(ROOT / "shadcn"))
    env.globals["_"] = lambda text: text
    return (
        '<div id="page-header">'
        + env.get_template("templates/copy_button.html").render(
            page={"markdown": MARKDOWN}
        )
        + "</div>"
    )


def clipboard_stub(page):
    page.add_init_script("""(() => {
      window.copiedText = null;
      Object.defineProperty(navigator, 'clipboard', {
        value: {writeText: text => {window.copiedText = text; return Promise.resolve();}},
        configurable: true
      });
    })()""")


@pytest.mark.parametrize(
    "page_url",
    [
        "https://thekrishna.in/Grove/latest/use-tui/",
        "https://code.example.org/team/Grove/latest/nested/use-tui/",
    ],
)
def test_copy_page_copies_embedded_markdown_without_fetch(
    page: Page, page_url: str
):
    requests = []
    page.route(
        "**/*",
        lambda route: (
            requests.append(route.request.url),
            route.fulfill(content_type="text/html", body=copy_markup()),
        ),
    )
    clipboard_stub(page)
    page.goto(page_url)
    page.add_script_tag(path=str(ROOT / "shadcn/js/copy-page.js"))
    page.locator("#page-header button").click()
    expect(page.locator("#page-header button")).to_have_attribute(
        "data-copy-state", "copied"
    )
    assert page.evaluate("window.copiedText") == MARKDOWN
    assert requests == [page_url]


@pytest.mark.parametrize("prefix", ["/Grove/latest/", "/team/Grove/1.2/"])
def test_build_info_uses_deployment_root(page: Page, prefix: str):
    page_url = "https://example.org" + prefix + "nested/use-tui/"
    build_url = "https://example.org" + prefix + "build-info.json"
    requests = []

    def handle(route):
        requests.append(route.request.url)
        if route.request.url == build_url:
            route.fulfill(
                content_type="application/json", body='{"commit":"abc123"}'
            )
        else:
            route.fulfill(
                content_type="text/html", body="<footer><p>Footer</p></footer>"
            )

    page.route("**/*", handle)
    page.goto(page_url)
    page.evaluate(
        """source => {
      const script = document.createElement('script');
      script.dataset.buildInfoUrl = '../../build-info.json';
      script.textContent = source;
      document.body.appendChild(script);
    }""",
        (ROOT / "shadcn/js/build-info.js").read_text(),
    )
    expect(page.locator(".build-info")).to_contain_text("build abc123")
    assert requests == [page_url, build_url]


def test_code_copy_handles_click_on_icon(page: Page):
    clipboard_stub(page)
    page.route(
        "**/*",
        lambda route: route.fulfill(
            content_type="text/html",
            body='<div class="codehilite"><pre><code>print(1)</code></pre></div>',
        ),
    )
    page.goto("https://example.org/docs/")
    page.add_script_tag(path=str(ROOT / "shadcn/js/callbacks.js"))
    page.add_script_tag(path=str(ROOT / "shadcn/js/copy-button.js"))
    page.locator(".codehilite button svg").dispatch_event("click")
    assert page.evaluate("window.copiedText") == "print(1)"


def test_copy_page_reports_clipboard_rejection(page: Page):
    page.set_content(copy_markup())
    page.evaluate("""() => Object.defineProperty(navigator, 'clipboard', {
      value: {writeText: () => Promise.reject(new Error('denied'))}, configurable: true
    })""")
    page.add_script_tag(path=str(ROOT / "shadcn/js/copy-page.js"))
    page.locator("#page-header button").click()
    expect(page.locator("#page-header button")).to_have_attribute(
        "data-copy-state", "failed"
    )
    expect(page.locator("#page-header button")).to_contain_text("Copy failed")
