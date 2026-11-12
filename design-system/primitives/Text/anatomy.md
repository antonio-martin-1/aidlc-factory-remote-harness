# Text — Anatomy

## Element structure

```tsx
<Tag class="text text--{variant}" style={{ color }}>
  {children}
</Tag>
```

## Required props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `variant` | See variants above | body | Text style variant |
| `color` | color token | color.neutral.text-primary | Text color |
| `align` | 'left' | 'center' | 'right' | left | Text alignment |
| `as` | element type | — | HTML element override (h1, p, span, etc.) |

## CSS class structure

```css
.text--h1 { font-size: font-size.h1; font-weight: font-weight.bold; }
.text--body { font-size: font-size.body; font-weight: font-weight.regular; }
.text--caption { font-size: font-size.caption; color: color.neutral.text-secondary; }
```
