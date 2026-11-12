# Input

Text input field for data entry.

## Constraints

| Property | Value |
|----------|-------|
| Height | 36px (md, default) |
| Border radius | `radius.sm` (3px) |
| Border | 1px solid `color.neutral.border` |
| Font size | `font-size.body` (14px) |
| Padding X | `spacing.md` (12px) |
| Padding Y | `spacing.sm` (8px) |

## Variants

| Variant | Purpose |
|---------|---------|
| `text` | Generic text input |
| `search` | Search field (may include search icon) |
| `password` | Password (hides input, shows toggle) |
| `number` | Numeric input |
| `email` | Email with validation |

## States

| State | Border | BG |
|-------|--------|----|
| Default | `color.neutral.border` | `color.neutral.bg` |
| Hover | `color.neutral.border` (darken 10%) | `color.neutral.bg` |
| Focus | `color.brand.primary` (2px ring) | `color.neutral.bg` |
| Error | `color.semantic.danger` | `color.semantic.danger-bg` |
| Disabled | `color.neutral.border` | `color.neutral.surface` (opacity 0.5) |

## Props

| Prop | Type | Description |
|------|------|-------------|
| `variant` | `'text' \| 'search' \| 'password' \| 'number' \| 'email'` | Input type |
| `label` | `string` | Visible label |
| `placeholder` | `string` | Placeholder text |
| `error` | `string` | Error message (shows below input) |
| `disabled` | `boolean` | Disabled state |
| `onChange` | `(value: string) => void` | Change handler |

## Accessibility

- MUST have associated `<label>` element
- MUST have `aria-describedby` when error is present
- MUST have `aria-invalid` when in error state
- MUST support `Tab` navigation

## When NOT to use

- Multi-line text → use `<textarea>`
- Select from options → use `<select>` / dropdown primitive
- Read-only display → use `Text`
- Date/time → use specialized date picker pattern

## Anatomy

```tsx
<Stack gap="xs">
  <label htmlFor={id}>{label}</label>
  <input
    id={id}
    type={variant}
    value={value}
    onChange={handleChange}
    disabled={disabled}
    aria-invalid={!!error}
    aria-describedby={error ? `${id}-error` : undefined}
  />
  {error && <Text variant="caption" color="danger">{error}</Text>}
</Stack>
```
