# Code-reference badges

The theme can render two families of inline **code-reference badges** from
ordinary markdown links, using custom `repo:` and `endpoint:` URI schemes. Turn
the feature on with `theme.code_refs` (see `mkdocs_theme.yml`); the styling
lives in `css/code-refs.css` and is loaded only when the feature is enabled.

## File references

A link of the form `[label](repo:<path>#L<start>-L<end>)` renders an octicon
pill that deep-links into the project repository at the build commit. The line
fragment is optional.

- A range: [`shadcn/plugins/mixins/code_refs.py`](repo:shadcn/plugins/mixins/code_refs.py#L134-L147)
- A single line: [`shadcn/main.html`](repo:shadcn/main.html#L5)
- No fragment (whole file): [`pyproject.toml`](repo:pyproject.toml)

Inside a fenced code block the scheme is left verbatim — markdown never turns it
into an anchor, so the hook can't touch it:

```text
[`app/main.py`](repo:app/main.py#L12-L20)
```

## Endpoint references

A link of the form `[label](endpoint:<METHOD> <path>)` renders a method-tinted
pill that deep-links into the configured API reference page, slugging the
matching tag anchor.

- [GET /api/users](endpoint:GET /api/users)
- [POST /api/users](endpoint:POST /api/users)
- [PATCH /api/items/{id}](endpoint:PATCH /api/items/42)
- [DELETE /api/items/{id}](endpoint:DELETE /api/items/42)
