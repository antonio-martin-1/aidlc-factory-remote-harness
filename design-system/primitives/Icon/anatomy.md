# Icon — Anatomy

## Element structure

```tsx
<svg class="icon icon--{size}" width={size} height={size} fill={color}>
  <use href={`#icon-{name}`} />
</svg>
```

## Required props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `name` | string | — | Icon identifier from the icon set |
| `size` | 'sm' | 'md' | 'lg' | 'xl' | md | Icon dimension (square) |
| `color` | color token | currentColor | Icon fill color |
| `set` | 'feather' | 'material' | 'custom' | feather | Icon set source |

## CSS class structure

```css
.icon { display: inline-block; flex-shrink: 0; }
.icon--sm { width: 16px; height: 16px; }
.icon--md { width: 20px; height: 20px; }
```
