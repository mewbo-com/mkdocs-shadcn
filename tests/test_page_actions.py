"""The copy button is a split control with a page-actions menu behind it.

Three things here are invisible to a build and to a screenshot:

The source URL. Every menu item but "Copy page" points at the page's Markdown
on the forge, and a wrong ref produces a link that looks perfect and 404s.
mkdocs' own default for `edit_uri` hardcodes `edit/master/docs/`, so deriving
from `page.edit_url` would 404 on any repo not published from `master` —
which is both consumers of this theme.

The Tailwind layer reclaiming the markup. `article button` in input.css sets a
2rem height and the primary (clay) variant on any unclassed button in the
article, which clamped the one <button> menu row to 32px against its <a>
siblings' 55px and painted the toggle clay beside its own grey other half.

The menu being dismissible. A dropdown that cannot be closed is worse than no
dropdown.
"""

import subprocess
from urllib.parse import unquote

import pytest
from playwright.sync_api import Page

MENU = "[data-mewbo-page-actions-menu]"
TOGGLE = "[data-mewbo-page-actions-toggle]"


def test_menu_items_point_at_the_page_source(
    page: Page, local_deployment: str
):
    page.goto(local_deployment + "/get_started/", wait_until="networkidle")

    links = page.evaluate(
        """() => {
          const href = sel => {
            const el = document.querySelector(sel);
            return el ? el.getAttribute('href') : null;
          };
          const items = [...document.querySelectorAll(
            '[data-mewbo-page-actions-menu] a[role="menuitem"]')];
          return {
            count: document.querySelectorAll(
              '[data-mewbo-page-actions-menu] [role="menuitem"]').length,
            hrefs: items.map(a => a.getAttribute('href')),
            // Every outbound item opens a new tab rather than navigating the
            // docs away from under the reader.
            targets: [...new Set(items.map(a => a.getAttribute('target')))],
            rels: [...new Set(items.map(a => a.getAttribute('rel')))],
          };
        }"""
    )

    assert links["count"] == 4, (
        f"expected 4 menu items, found {links['count']} — check that "
        "repo_url is set so the source-backed items render"
    )
    assert links["targets"] == ["_blank"], links["targets"]
    assert all("noopener" in (r or "") for r in links["rels"]), links["rels"]

    source, chatgpt, claude = links["hrefs"]

    assert source.startswith("https://raw.githubusercontent.com/"), source
    assert "/refs/heads/" in source and source.endswith(".md"), source
    # The ref must not be mkdocs' invented default, which is the 404 case.
    assert "/refs/heads/master/" not in source or "master" in _repo_branch(
        page
    ), (
        f"source URL pins the branch to master ({source}) — that is mkdocs' "
        "hardcoded edit_uri default, not a branch anyone chose"
    )

    # One line, naming the URL. Not the page text: a prompt carrying a whole
    # document is a fragile URL and goes stale as soon as the page changes.
    for target, prefix in (
        (chatgpt, "https://chatgpt.com/?prompt="),
        (claude, "https://claude.ai/new?q="),
    ):
        assert target.startswith(prefix), target
        prompt = unquote(target[len(prefix) :])
        assert prompt == f"Read {source} so I can ask questions about it."
        # Encoding is what stops a URL containing & or # from truncating the
        # prompt, so the raw href must not carry the separators literally.
        assert " " not in target[len(prefix) :], (
            f"the prompt is not URL-encoded: {target}"
        )


@pytest.mark.parametrize("width", [390, 1440])
def test_menu_icons_and_labels_share_left_alignment(
    page: Page, local_deployment: str, width: int
):
    page.set_viewport_size({"width": width, "height": 900})
    page.goto(local_deployment + "/get_started/", wait_until="networkidle")
    page.locator(TOGGLE).click()
    rows = page.locator(MENU + " [role=menuitem]").evaluate_all("""rows =>
      rows.map(row => ({
        icon:row.querySelector('.mewbo-page-action__icon').getBoundingClientRect().left,
        label:row.querySelector('.mewbo-page-action__label').getBoundingClientRect().left
      }))""")
    assert len(rows) == 4
    for column in ("icon", "label"):
        positions = [row[column] for row in rows]
        assert max(positions) - min(positions) < 1, (column, positions)


def _repo_branch(page: Page) -> str:
    """The branch this checkout is on, for the assertion above."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


@pytest.mark.parametrize("dark", [False, True])
def test_split_button_reads_as_one_control(
    page: Page, local_deployment: str, dark: bool
):
    page.goto(local_deployment + "/get_started/", wait_until="networkidle")
    page.evaluate(
        "dark => document.documentElement.classList.toggle('dark', dark)", dark
    )
    # Open without leaving the pointer on the toggle, or its :hover state is
    # what gets measured rather than its resting one.
    page.evaluate(f"document.querySelector('{TOGGLE}').click()")
    page.mouse.move(10, 600)

    metrics = page.evaluate(
        """() => {
          const toggle = document.querySelector(
            '[data-mewbo-page-actions-toggle]');
          const main = document.querySelector('.mewbo-page-actions__main');
          const rows = [...document.querySelectorAll('.mewbo-page-action')]
            .map(el => Math.round(el.getBoundingClientRect().height));
          return {
            toggleBg: getComputedStyle(toggle).backgroundColor,
            mainBg: getComputedStyle(main).backgroundColor,
            rows,
          };
        }"""
    )

    # The two halves are one control. `article button:where(:not(.secondary…))`
    # claimed the toggle as the primary variant and painted it clay.
    assert metrics["toggleBg"] == metrics["mainBg"], (
        f"the toggle ({metrics['toggleBg']}) and the copy button "
        f"({metrics['mainBg']}) are different colours — they read as two "
        "controls, not one split button"
    )

    # The "Copy page" row is a <button>, the rest are <a>. `article button`
    # clamps a button to 2rem, which cropped that row and spilled its hint
    # text onto the row below.
    assert len(metrics["rows"]) == 4, metrics["rows"]
    assert len(set(metrics["rows"])) == 1, (
        f"menu rows have differing heights {metrics['rows']} — the <button> "
        "row is being clamped by the article's own button height"
    )


def test_menu_can_be_dismissed(page: Page, local_deployment: str):
    page.goto(local_deployment + "/get_started/", wait_until="networkidle")

    def open_menu():
        page.evaluate(f"document.querySelector('{TOGGLE}').click()")
        assert (
            page.evaluate(f"document.querySelector('{MENU}').hidden") is False
        ), "the menu did not open"

    open_menu()
    page.keyboard.press("Escape")
    assert page.evaluate(f"document.querySelector('{MENU}').hidden"), (
        "Escape does not close the menu"
    )

    open_menu()
    page.mouse.click(60, 700)
    assert page.evaluate(f"document.querySelector('{MENU}').hidden"), (
        "clicking outside does not close the menu"
    )

    # aria-expanded has to track the real state, or a screen reader is told
    # the menu is shut while it is open.
    open_menu()
    assert page.get_attribute(TOGGLE, "aria-expanded") == "true"
    page.keyboard.press("Escape")
    assert page.get_attribute(TOGGLE, "aria-expanded") == "false"


def test_copy_proxy_copies_and_closes(page: Page, local_deployment: str):
    """The menu's copy row delegates to the main button rather than
    re-implementing the clipboard write, so there is one copy path."""
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    page.goto(local_deployment + "/get_started/", wait_until="networkidle")

    page.evaluate(f"document.querySelector('{TOGGLE}').click()")
    page.evaluate("document.querySelector('[data-mewbo-copy-proxy]').click()")
    page.wait_for_timeout(200)

    assert page.get_attribute("[data-copy-markdown]", "data-copy-state") == (
        "copied"
    ), "the menu's copy row did not reach the copy handler"
    assert page.evaluate(f"document.querySelector('{MENU}').hidden"), (
        "the menu stayed open after copying"
    )
    assert page.evaluate("navigator.clipboard.readText()").startswith("##"), (
        "the clipboard does not hold the page Markdown"
    )

    # 'Copied' is an acknowledgement, not a mode: it has to time out, or a
    # second copy gives no feedback at all.
    page.wait_for_timeout(2200)
    assert page.get_attribute("[data-copy-markdown]", "data-copy-state") == (
        "ready"
    ), "the copied state never reset"
