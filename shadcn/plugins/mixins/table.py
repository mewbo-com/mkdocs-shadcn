import re

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import get_plugin_logger
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page

from shadcn.plugins.mixins.base import Mixin

logger = get_plugin_logger("mixins/table")

# A bare opening tag only — a classed `<table class=...>` is pygments', not
# prose. Non-greedy so consecutive tables each get their own wrapper.
_PROSE_TABLE_RE = re.compile(r"<table>(.*?)</table>", re.DOTALL)


class TableMixin(Mixin):
    """A mixin to wrap <table> to better manage overflow"""

    def on_page_content(
        self,
        html: str,
        page: Page,
        config: MkDocsConfig,
        files: Files,
    ) -> str:
        # Only PROSE tables. Markdown emits a bare `<table>`; pygments emits
        # `<table class="codehilitetable">` for a code block's line-number
        # gutter. The old blanket string replace wrapped that one too, so a
        # numbered code block got a prose table's overflow wrapper and full
        # width, which pushed its code away from the left edge.
        html = _PROSE_TABLE_RE.sub(
            r'<div class="table-wrapper"><table>\1</table></div>',
            html,
        )
        return super().on_page_content(html, page, config, files)
