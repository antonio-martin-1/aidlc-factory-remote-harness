# Stack — Anatomy

## Element structure

```tsx
<div class="stack" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap)' }}>
  {children}
</div>
```

## Required props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `gap` | spacing token | spacing.md | Vertical gap between children |
| `align` | 'start' | 'center' | 'end' | 'stretch' | stretch | Cross-axis alignment |
| `padding` | spacing token | — | Inner padding |
| `radius` | radius token | — | Container border radius |

## CSS class structure

```css
.stack { display: flex; flex-direction: column; width: 100%; }
.stack--align-center { align-items: center; }
.stack--align-end { align-items: flex-end; }
```
