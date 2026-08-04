# Mermaid

Fenced ` ```mermaid ` blocks render as diagrams. Each one becomes a framed
figure you can expand: hover it and press **Expand**, or click the figure, to
open a viewer with zoom and pan.

Diagrams are drawn from the site's own colour tokens and typeface, and they
follow the light/dark toggle without a reload.

!!! note "Enabling it"

    The theme ships the renderer, but the fence has to be routed to it by
    `pymdownx.superfences`. Add this to your `mkdocs.yml`:

    ```yaml
    markdown_extensions:
      pymdownx.superfences:
        custom_fences:
          - name: mermaid
            class: mermaid
            format: !!python/name:pymdownx.superfences.fence_code_format
    ```

    Without it a `mermaid` fence is highlighted as plain source and no
    diagram appears.

## Flowchart

```mermaid
flowchart LR
    A[Author writes a fence] --> B{Superfences routes it?}
    B -- yes --> C[Rendered as a diagram]
    B -- no --> D[Highlighted as source]
    C --> E[Framed figure on the page]
    E --> F[Expand to zoom and pan]
```

## Multi-line labels

Labels wrap onto several lines when they are long, and a `<br/>` forces a
break where you want one. Both are set at the diagram's own leading rather
than the browser default, so a multi-line node sits correctly beside a
single-line one.

```mermaid
flowchart TD
    Start["Ingest the repository<br/>and walk its file tree"]
    Parse["Parse each file into an AST, then resolve symbols across files"]
    Graph["Build the code graph"]
    Pages["Generate documentation pages<br/>grounded in the graph"]

    Start --> Parse --> Graph --> Pages
```

## Sequence

```mermaid
sequenceDiagram
    participant R as Reader
    participant P as Page
    participant V as Viewer

    R->>P: Opens a page containing a diagram
    P->>P: Renders the fence with the page's tokens
    R->>V: Clicks Expand
    V-->>R: Opens with the diagram fitted to the stage
    R->>V: Scrolls to zoom, drags to pan
    R->>V: Presses Escape
    V-->>P: Closes, page position unchanged
```

## Wide diagrams

A diagram wider than the column is scaled down to fit the figure. Expanding
it restores full size, so nothing is lost to the column width.

```mermaid
flowchart LR
    A[Clone] --> B[Scan] --> C[Graph] --> D[Enrich] --> E[Plan] --> F[Generate] --> G[Finalize] --> H[Publish]
```

## Tall diagrams

A very tall diagram is bounded inside its figure so it cannot push the
surrounding prose apart. The full height is available in the viewer.

```mermaid
flowchart TD
    N1[Request arrives] --> N2[Authenticate]
    N2 --> N3[Resolve the workspace]
    N3 --> N4[Load session state]
    N4 --> N5[Bind the tool registry]
    N5 --> N6[Start the turn]
    N6 --> N7[Call the model]
    N7 --> N8{Tool requested?}
    N8 -- yes --> N9[Dispatch the tool]
    N9 --> N7
    N8 -- no --> N10[Emit the answer]
    N10 --> N11[Persist the transcript]
    N11 --> N12[Close the turn]
```

## Class diagram

```mermaid
classDiagram
    class Renderer {
        +render(source) SVG
        -cache Map
    }
    class Viewer {
        +open(figure)
        +fit()
        -scale float
    }
    Renderer <|-- Viewer : shares the cache
```

## State diagram

```mermaid
stateDiagram-v2
    [*] --> Pending
    Pending --> Rendered : mermaid resolves
    Pending --> Failed : source is invalid
    Rendered --> Expanded : reader clicks Expand
    Expanded --> Rendered : Escape
    Failed --> [*]
```
