# Icon

SVG icon wrapper. Provides consistent sizing, coloring, and accessibility.

## Constraints

| Property | Value |
|----------|-------|
| Size | Must be 16, 20, 24, or 32px |
| Color | Must be a `color` token |
| ViewBox | `0 0 24 24` (default) |

## Sizes

| Token | Pixels | Used for |
|-------|--------|----------|
| `icon-size.sm` | 16 | Inline with caption text |
| `icon-size.md` | 20 | Inline with body text |
| `icon-size.lg` | 24 | Standalone, button icons |
| `icon-size.xl` | 32 | Empty states, feature icons |

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `name` | `string` | — | Icon identifier |
| `size` | `'sm' \| 'md' \| 'lg' \| 'xl'` | `'md'` | Icon size |
| `color` | `color token` | `color.neutral.icon` | Icon color |
| `aria-label` | `string` | — | Accessible label |

## Accessibility

- Decorative icons: `aria-hidden="true"` (no label needed)
- Informational icons: MUST have `aria-label`
- Button icons: use Button's `icon` prop instead of rendering Icon directly

## When NOT to use

- Images/photos → use `<img>`
- Complex illustrations → use SVG directly or `<img>`
- Loading indicators → use a spinner pattern, not an icon

## Anatomy

```tsx
<Icon name="search" size="md" color={color.neutral.icon} aria-hidden="true" />
```
