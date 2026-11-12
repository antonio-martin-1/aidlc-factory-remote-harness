# Anti-pattern: Broken Spacing

**BAD**: Using arbitrary padding/margin values outside the token set.

```tsx
// ❌ BAD — arbitrary values
<div style={{ padding: '7px', margin: '14px' }}>
<Button style={{ paddingLeft: '11px' }}>
```

**GOOD**: Use spacing tokens from `tokens/spacing.md`.

```tsx
// ✅ GOOD — canonical token values
<Box padding="sm">       {/* 8px — nearest snap from 7 */}
<Stack gap="lg" />        {/* 16px — nearest snap from 14 */}
<Button paddingX="md" />  {/* 12px — nearest snap from 11 */}
```

## Why this is an anti-pattern

- 7 and 14 are not in the token set (4, 8, 12, 16, 24, 32)
- Inconsistent spacing creates visual noise
- Breaks alignment across sections
- Makes future theming impossible

## Snap rule

If you see any padding/margin/gap value not in `{4, 8, 12, 16, 24, 32}`, snap to the nearest canonical value.
