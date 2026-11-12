# Stack

Vertical layout container. Arranges children top-to-bottom with consistent gap.

## Constraints

| Property | Value |
|----------|-------|
| Display | `flex`, `flex-direction: column` |
| Gap | One of `spacing.xs` through `spacing.xxl` (never arbitrary) |
| Width | Defaults to 100% of parent |
| Alignment | `start` (default), `center`, `end`, `stretch` |

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `gap` | `spacing token` | `spacing.md` | Vertical gap between children |
| `align` | `'start' \| 'center' \| 'end' \| 'stretch'` | `'stretch'` | Cross-axis alignment |

## When NOT to use

- Horizontal layouts → use `Inline`
- Grid layouts → use CSS Grid
- Single child → just render the child directly

## Anatomy

```tsx
<Stack gap="md" align="stretch">
  {children}
</Stack>
```
