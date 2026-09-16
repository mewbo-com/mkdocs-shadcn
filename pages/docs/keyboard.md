# Keyboard shortcuts

Write shortcuts as `++key+key++` and they render as real `<kbd>` elements
rather than prose or inline code.

Keycaps are drawn entirely in CSS, in the page's own typeface — no webfont,
local or remote. Each cap is lit from above: a bright lip along the top of
the face, darker side walls, and a deeper front wall with the cap's shadow
under it. That asymmetry is what makes it read as something you press rather
than as a bordered badge. Colours derive from `--muted`, so caps invert with
the theme and follow a brand fork's palette without any further work.

Every label is styled identically, including `Cmd` and the arrows, and caps
are sized in `em`, so they track the type around them in prose, in a table
cell, or in a heading.

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
