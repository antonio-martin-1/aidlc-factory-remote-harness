# Pattern: Data Table

Composition of Surface + Text + Inline + Box for tabular data display.

## Structure

```
Surface (level="level-1", radius="md")
  └── Stack
       ├── Inline (gap="md")       — Toolbar
       │   ├── Text (variant="h4")
       │   ├── (spacer)
       │   └── Button (action)
       ├── <table>                 — Data rows
       │   ├── <thead>
       │   │   └── <tr> <th />* </tr>
       │   └── <tbody>
       │       └── <tr> <td />* </tr>
       └── Inline (gap="sm")       — Pagination
            ├── Button (icon, previous)
            ├── Text (variant="caption", "Page X of Y")
            └── Button (icon, next)
```

## Rules

1. Header row: `color.neutral.surface` background, `font-weight.semibold`
2. Alternating row background optional (only if >10 rows)
3. Sortable columns: show arrow icon in header
4. Empty state: show Text + Icon centered
5. Pagination below table, centered

## When to use

- Lists of records with columns
- Data that needs sorting/pagination

## When NOT to use

- < 5 items → use a list pattern instead
- Card-based layouts → use card-grid pattern
