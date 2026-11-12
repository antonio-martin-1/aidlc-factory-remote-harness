# Anti-pattern: Custom Padding

**BAD**: Inline style or arbitrary className that hardcodes padding values.

```tsx
// ❌ BAD — hardcoded custom padding
<div style={{ padding: '13px 7px' }}>
<button className="px-[13px] py-[7px]">

// ❌ BAD — utility classes with arbitrary values
<div className="px-[9px]">
<button className="pt-[5px] pb-[5px]">
```

**GOOD**: Use design system primitives and spacing tokens.

```tsx
// ✅ GOOD — Box with spacing tokens
<Box padding="md">        {/* 12px — nearest snap from 13 */}
<Button size="sm" />      {/* knows its own padding */}

// ✅ GOOD — Stack with token gap
<Stack gap="sm">          {/* 8px — nearest snap from 7 */}
```

## Why this is an anti-pattern

- Tailwind's arbitrary value syntax `px-[13px]` is the #1 source of UI drift
- Hardcoded values bypass the design system entirely
- Future theming/redesign becomes a manual hunt for every hardcoded value
- 13px doesn't match any canonical spacing token

## Rule

- Never use Tailwind arbitrary value syntax (`px-[...]`, `py-[...]`, `gap-[...]`)
- Never inline `style={{ padding: ... }}` in UI components
- Always resolve through a primitive (Box, Stack) or a spacing token
- Validator autocorrects: `13px → 12px`, `5px → 4px`, `7px → 8px`
