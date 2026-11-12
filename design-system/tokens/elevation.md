# Elevation Tokens

Allowed shadow and z-index values.

## Shadow scale

| Token | Value | Used for |
|-------|-------|----------|
| `elevation.none` | none | Flat surfaces |
| `elevation.sm` | `0 1px 2px rgba(0,0,0,0.05)` | Cards, subtle elevation |
| `elevation.md` | `0 4px 6px -1px rgba(0,0,0,0.1)` | Dropdowns, popovers |
| `elevation.lg` | `0 10px 15px -3px rgba(0,0,0,0.1)` | Modals, dialogs |
| `elevation.xl` | `0 20px 25px -5px rgba(0,0,0,0.15)` | Top-level overlays, toasts |

## Z-index scale

| Token | Value | Used for |
|-------|-------|----------|
| `z.base` | 1 | Sticky elements |
| `z.dropdown` | 10 | Dropdowns, popovers |
| `z.sticky` | 50 | Sticky headers |
| `z.modal` | 100 | Modal backdrops |
| `z.modal-content` | 110 | Modal content |
| `z.toast` | 200 | Toasts, notifications |

## Snap rules

| If shadow resembles | Snap to |
|--------------------|---------|
| 0-2px blur, any color | `elevation.sm` |
| 3-6px blur, any color | `elevation.md` |
| 7-15px blur, any color | `elevation.lg` |
| 16+ px blur, any color | `elevation.xl` |
