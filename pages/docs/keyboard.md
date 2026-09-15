# Keyboard shortcuts

Write shortcuts as `++key+key++` and they render as real `<kbd>` elements
rather than prose or inline code. Keycaps use the locally bundled Libertinus
Keyboard font at an enlarged optical size with spacing around each key. The
font draws its own outline without an extra container. Modifier names not
supported by its ligatures retain readable text with a single CSS outline.
No external font service is required.

| Shortcut | Written as |
|---|---|
| ++ctrl+shift+a++ | `++ctrl+shift+a++` |
| ++cmd+shift+p++ | `++cmd+shift+p++` |
| ++cmd+opt+z++ | `++cmd+opt+z++` |
| ++windows+r++ | `++windows+r++` |
| ++alt+f4++ | `++alt+f4++` |
| ++ctrl+k++ | `++ctrl+k++` |
| ++enter++ | `++enter++` |
| ++shift+tab++ | `++shift+tab++` |
| ++arrow-up++ ++arrow-down++ | `++arrow-up++ ++arrow-down++` |

Both platforms are covered. `cmd` renders the Command key and `opt` the
Option key; `windows` renders the Windows key. Use the modifier the platform
you are documenting actually uses, and give both when a shortcut differs:
press ++cmd+k++ on macOS or ++ctrl+k++ elsewhere to open search.
