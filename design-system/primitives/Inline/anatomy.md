# Inline — Anatomy

## Element structure

```tsx
<div class="inline" style={{ display: 'flex', flexDirection: 'row', gap: 'var(--gap)', flexWrap: wrap ? 'wrap' : 'nowrap' }}>
  {children}
</div>
```

## Required props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `gap` | spacing token | spacing.sm | Horizontal gap between children |
| `align` | 'start' | 'center' | 'end' | 'stretch' | center | Cross-axis alignment |
| `wrap` | boolean | false | Allow wrapping to next line |
| `padding` | spacing token | — | Inner padding |

## CSS class structure

```css
.inline { display: flex; flex-direction: row; align-items: center; }
.inline--wrap { flex-wrap: wrap; }
```
