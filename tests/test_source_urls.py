"""Source actions use GitHub's raw content host without a redirect."""

from types import SimpleNamespace

import pytest

from shadcn.filters import page_source_url


@pytest.mark.parametrize(
    "repo,ref,path,edit_uri,expected",
    [
        (
            "https://github.com/bearlike/Grove",
            "current",
            "index.md",
            "edit/master/docs/",
            "https://raw.githubusercontent.com/bearlike/Grove/refs/heads/current/docs/index.md",
        ),
        (
            "https://github.com/bearlike/Assistant",
            "master",
            "getting-started.md",
            "edit/master/docs/",
            "https://raw.githubusercontent.com/bearlike/Assistant/refs/heads/master/docs/getting-started.md",
        ),
        (
            "https://github.com/acme/docs.git/",
            "release/docs",
            "guides/using keys.md",
            None,
            "https://raw.githubusercontent.com/acme/docs/refs/heads/release/docs/docs/guides/using%20keys.md",
        ),
        (
            "https://github.com/acme/docs",
            "main",
            "install.md",
            "edit/published/manual/",
            "https://raw.githubusercontent.com/acme/docs/refs/heads/published/manual/install.md",
        ),
        (
            "https://github.com/acme/docs",
            "main",
            "install.md",
            "blob/published/manual/",
            "https://raw.githubusercontent.com/acme/docs/refs/heads/published/manual/install.md",
        ),
        (
            "https://github.com/acme/docs",
            "main",
            "install.md",
            "https://raw.githubusercontent.com/acme/docs/refs/heads/published/manual/",
            "https://raw.githubusercontent.com/acme/docs/refs/heads/published/manual/install.md",
        ),
        (
            "https://code.example.org/team/docs",
            "main",
            "install.md",
            "raw/branch/main/docs/",
            "https://code.example.org/team/docs/raw/branch/main/docs/install.md",
        ),
    ],
)
def test_source_actions_use_canonical_raw_urls(
    repo, ref, path, edit_uri, expected
):
    page = SimpleNamespace(file=SimpleNamespace(src_uri=path))
    config = {
        "repo_url": repo,
        "theme": {"source_ref": ref},
        "edit_uri": edit_uri,
    }
    assert page_source_url(page, config) == expected


def test_no_repository_has_no_source_actions():
    page = SimpleNamespace(file=SimpleNamespace(src_uri="index.md"))
    assert page_source_url(page, {"theme": {"source_ref": "main"}}) == ""
