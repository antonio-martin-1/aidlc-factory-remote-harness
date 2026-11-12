# Surface

Themed background container. Used for sections, modals, sidebars, banners.

## Constraints

| Property | Value |
|----------|-------|
| Border radius | Must be a `radius` token |
| Padding | Must be a `spacing` token |
| Background | One of the defined surface color tokens |

## Levels

| Level | Background | Border | Used for |
|-------|-----------|--------|----------|
| `level-0` | `color.neutral.bg` | None | Default page surface |
| `level-1` | `color.neutral.surface` | `color.neutral.border` | Cards, panels |
| `level-2` | `color.neutral.surface` + `elevation.sm` | `color.neutral.border` | Elevated cards, dropdowns |
| `level-brand` | `color.brand.primary` | None | Brand banners, hero sections |
| `level-danger` | `color.semantic.danger-bg` | `color.semantic.danger` | Error alerts |
| `level-success` | `color.semantic.success-bg` | `color.semantic.success` | Success alerts |

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `level` | See above | `'level-1'` | Surface level |
| `padding` | `spacing token` | `spacing.lg` | Inner padding |
| `radius` | `radius token` | `radius.md` | Border radius |

## When NOT to use

- Inline formatting → use `Box` or native elements
- Semantic HTML sections → use `<section>`, `<article>`, `<aside>`, `<nav>`

## Anatomy

```tsx
<Surface level="level-1" padding="lg" radius="md">
  {children}
</Surface>
```
