# Code blocks

The theme styles the markup `pymdownx.highlight` emits: fence titles, the
line-number table, highlighted lines, and inline highlighting.

## A titled block

```python title="app.py"
def greet(name: str) -> str:
    return f"hello {name}"
```

## Line numbers

```python linenums="1"
def fib(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
```

## Highlighted lines

```python linenums="1" hl_lines="2 3"
def load(path):
    with open(path) as fh:
        return fh.read()
```

## Titled, numbered and highlighted together

```yaml title="mkdocs.yml" linenums="1" hl_lines="3"
theme:
  name: shadcn
  code_refs:
    endpoint:
      reference_page: reference/
```

## Inline highlighting

Call `#!python greet("world")` inline, beside a plain `code` span so the two
can be compared.

## A long block

```python linenums="1"
class Example:
    """Long enough to exercise the block's own height cap."""

    def one(self): return 1
    def two(self): return 2
    def three(self): return 3
    def four(self): return 4
    def five(self): return 5
    def six(self): return 6
    def seven(self): return 7
    def eight(self): return 8
    def nine(self): return 9
    def ten(self): return 10
    def eleven(self): return 11
    def twelve(self): return 12
    def thirteen(self): return 13
    def fourteen(self): return 14
    def fifteen(self): return 15
```
