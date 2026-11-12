# Box — Anatomy

## Element structure

```tsx
<div class="box" style={{ padding, borderRadius, backgroundColor, boxShadow }}>
  {children}
</div>
```

## Required props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `padding` | spacing token | — | Inner padding |
| `radius` | radius token | radius.none | Border radius |
| `background` | color token | — | Background color |
| `border` | color token | — | Border color |

## CSS class structure

```css
.box { box-sizing: border-box; }
.box--elevated { box-shadow: var(--elevation); }
.box--outlined { border: 1px solid color.neutral.border; }
```
