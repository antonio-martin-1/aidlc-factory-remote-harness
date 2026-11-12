# Button — Anatomy

## Element structure

```
<button class="btn btn-{variant} btn-{size}">
  {Icon ? <Icon name={iconName} size={iconSize} /> : null}
  {label}
  {badge ? <span class="btn-badge">{badge}</span> : null}
</button>
```

## Required props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `variant` | `'primary' \| 'secondary' \| 'ghost' \| 'danger' \| 'icon'` | `'primary'` | Visual style |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` | Button size |
| `label` | `string` | — | Button text (omit for icon variant) |
| `onClick` | `() => void` | — | Click handler |

## Optional props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `disabled` | `boolean` | `false` | Disabled state |
| `icon` | `string` | — | Icon name (prefixes label) |
| `iconPosition` | `'left' \| 'right'` | `'left'` | Icon placement |
| `badge` | `string \| number` | — | Badge count |
| `loading` | `boolean` | `false` | Show spinner, disable clicks |
| `type` | `'button' \| 'submit' \| 'reset'` | `'button'` | HTML type |
| `aria-label` | `string` | — | Required for icon-only |
| `data-testid` | `string` | — | Required for E2E tests |

## CSS class structure

```css
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: spacing.sm;
  border-radius: radius.sm;
  font-size: font-size.body;
  font-weight: font-weight.medium;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background-color 0.15s, opacity 0.15s;
}

.btn--primary {
  background-color: color.brand.primary;
  color: #FFFFFF;
}

.btn--ghost {
  background-color: transparent;
  color: color.neutral.text-primary;
}

/* ... per variant */
```

## Layout rules

1. Icon + label: gap `spacing.sm` (8px)
2. Icon-only (variant=icon): width = height (square)
3. Badge positioned to the right of label with `spacing.xs` gap
4. Loading spinner replaces icon when `loading=true`
