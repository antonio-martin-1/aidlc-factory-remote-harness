# Text

Typography element for non-interactive text content.

## Constraints

| Property | Value |
|----------|-------|
| Font size | Must be a `font-size` token |
| Font weight | Must be a `font-weight` token |
| Line height | Must be a `line-height` token |
| Color | Must be a `color.neutral.text-*` or `color.semantic.*` token |

## Variants

| Variant | Font size | Weight | Used for |
|---------|-----------|--------|----------|
| `h1` | `font-size.h1` | `font-weight.bold` | Page titles |
| `h2` | `font-size.h2` | `font-weight.bold` | Section headings |
| `h3` | `font-size.h3` | `font-weight.semibold` | Sub-section headings |
| `h4` | `font-size.h4` | `font-weight.semibold` | Card titles |
| `body` | `font-size.body` | `font-weight.regular` | Body text, paragraphs |
| `body-large` | `font-size.body-large` | `font-weight.regular` | Lead paragraphs |
| `caption` | `font-size.caption` | `font-weight.regular` | Metadata, footnotes |
| `label` | `font-size.body` | `font-weight.medium` | Form labels |

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `variant` | See above | `'body'` | Text variant |
| `color` | `color token` | `color.neutral.text-primary` | Text color |
| `align` | `'left' \| 'center' \| 'right'` | `'left'` | Text alignment |

## When NOT to use

- Interactive text → use `Button` or `<a>`
- Input labels → use `<label>` with `variant="label"`
- SVG text → use `<text>` SVG element

## Anatomy

```tsx
<Text variant="h1">Page Title</Text>
<Text variant="body" color={color.neutral.text-secondary}>
  Description paragraph.
</Text>
<Text variant="caption">Last updated: Jan 2026</Text>
```
