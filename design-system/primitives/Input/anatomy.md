# Input — Anatomy

## Element structure

```tsx
<div class="input-wrapper">
  {label ? <label>{label}</label> : null}
  <input class="input input--{size}" type="{type}" placeholder="{placeholder}" />
  {error ? <span class="input-error">{error}</span> : null}
</div>
```

## Required props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `variant` | 'outlined' | 'filled' | outlined | Input style |
| `size` | 'sm' | 'md' | 'lg' | md | Input height |
| `placeholder` | string | — | Placeholder text |
| `value` | string | — | Controlled value |

## CSS class structure

```css
.input { border: 1px solid color.neutral.border; border-radius: radius.sm; }
.input--error { border-color: color.semantic.danger; }
.input:focus { outline: 2px solid color.brand.primary; }
```
