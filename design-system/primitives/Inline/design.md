# Inline

Horizontal layout container. Arranges children left-to-right with consistent gap.

## Constraints

| Property | Value |
|----------|-------|
| Display | `flex`, `flex-direction: row` |
| Gap | One of `spacing.xs` through `spacing.xxl` (never arbitrary) |
| Wrap | `wrap` by default (overflow goes to next line) |
| Alignment | `center` (default vertical), `start`, `end`, `stretch` |

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `gap` | `spacing token` | `spacing.sm` | Horizontal gap between children |
| `align` | `'start' \| 'center' \| 'end' \| 'stretch'` | `'center'` | Cross-axis alignment |
| `wrap` | `boolean` | `true` | Allow wrapping to next line |

## When NOT to use

- Vertical layouts → use `Stack`
- Single child → just render the child directly
- Grid/list of items → use proper list with `Stack`

## Anatomy

```tsx
<Inline gap="sm" align="center" wrap={true}>
  {children}
</Inline>
```
