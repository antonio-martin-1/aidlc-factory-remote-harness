# Surface — Anatomy

## Element structure

```tsx
<div class="surface surface--{variant}">
  {children}
</div>
```

## Required props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `variant` | 'elevated' | 'outlined' | 'filled' | elevated | Surface style |
| `padding` | spacing token | spacing.lg | Inner padding |
| `radius` | radius token | radius.lg | Border radius |

## CSS class structure

```css
.surface { box-sizing: border-box; }
.surface--elevated { box-shadow: var(--elevation); }
.surface--outlined { border: 1px solid color.neutral.border; }
```
