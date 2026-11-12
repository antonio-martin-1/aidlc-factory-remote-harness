# Box

Generic surface container with configurable padding and border-radius.

## Constraints

| Property | Value |
|----------|-------|
| Padding | Must be a single `spacing` token (applied to all sides) |
| Border radius | Must be a `radius` token |
| Background | Optional, defaults to transparent |
| Border | Optional, defaults to none |

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `padding` | `spacing token` | `spacing.md` | Inner padding |
| `radius` | `radius token` | `radius.md` | Border radius |
| `bg` | `color token` | — | Background color |
| `border` | `color token` | — | Border color (adds 1px solid) |
| `elevation` | `elevation token` | `elevation.none` | Box shadow |

## When NOT to use

- When you just need a plain div → use raw `<div>`
- When you need semantic HTML (`<section>`, `<article>`, `<nav>`) → use semantic element
- When you need a clickable container → use a pattern from `patterns/`

## Anatomy

```tsx
<Box padding="md" radius="md" bg={color.neutral.surface} elevation="sm">
  {children}
</Box>
```
