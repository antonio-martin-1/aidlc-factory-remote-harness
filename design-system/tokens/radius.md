# Border Radius Tokens

Allowed border-radius values.

## Scale

| Token | Pixels | Used for |
|-------|--------|----------|
| `radius.none` | 0 | Sharp edges, tables, inputs |
| `radius.sm` | 3 | Buttons, small components, badges |
| `radius.md` | 6 | Cards, modals, surfaces |
| `radius.lg` | 12 | Dialogs, large panels |
| `radius.full` | 9999 | Pills, tags, circular avatars |

## Snap rules

| If radius is | Snap to |
|--------------|---------|
| 0-1 | 0 (none) |
| 2-4 | 3 (sm) |
| 5-9 | 6 (md) |
| 10-16 | 12 (lg) |
| 17+ | 9999 (full) |
