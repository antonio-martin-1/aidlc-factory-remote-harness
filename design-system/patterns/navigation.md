# Pattern: Navigation

Composition of Inline + Button + Icon for toolbars and nav bars.

## Structure (horizontal)

```
Surface (level="level-0", border-bottom)
  └── Inline (gap="xs", align="center")
       ├── Icon (logo)
       ├── Text (variant="h4", brand)
       ├── (spacer)
       ├── Button (variant="ghost", label="Nav 1")
       ├── Button (variant="ghost", label="Nav 2")
       ├── Button (variant="ghost", label="Nav 3")
       └── Button (variant="primary", label="CTA")
```

## Rules

1. Active item uses `variant="primary"` (ghost variant with brand text)
2. Max 5 nav items. If >5, use dropdown overflow pattern
3. Logo always left, CTA always right
4. Responsive: collapse to hamburger below 768px

## When to use

- Top navigation bars
- Sidebar navigation
- Tab bars

## When NOT to use

- Breadcrumbs → use Text with "/" separators
- Pagination → use data-table pattern
