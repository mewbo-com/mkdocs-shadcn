---
title: Reading focus regression
summary: Regression fixture — quiet navigation rails, serif tab labels, and code that stands out inside callouts
---

The prose column is where a reader looks. The navigation rails on either side
stay a clear step smaller than this paragraph, and hovering one of their rows
only brightens the text.

## Tabs name their panels

=== "uv (recommended)"

    Install with `uv tool install example`, then run `example --version`.

    ```bash
    uv tool install example
    ```

=== "pipx"

    Install with `pipx install example`.

=== "pip"

    Install with `pip install example`.

## Code inside a callout

!!! warning "The distribution is `example-dist`, not `example`"

    A bare `uv tool install example` (or `pipx`, `pip`) installs a different
    package and fails with `Failed to initialise configuration handler`. The
    command this one installs is still `example`, and `example --version`
    prints `example-dist 1.0` when it is right.

    ```bash
    uv tool install example-dist
    ```

## Stacked inline code

Short lines with a code span on each line: `alpha_setting` and `beta_setting`
sit on this line, `gamma_setting` and `delta_setting` on the next, and
`epsilon_setting` with `zeta_setting` on the one after that, so a chip on one
line sits directly above a chip on the next line wherever the text wraps.
