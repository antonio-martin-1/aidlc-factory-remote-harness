# Spacing Tokens

Allowed spacing values for padding, margin, and gap.
Any value not in this set MUST be snapped to the nearest canonical value.

## Scale

| Token | Pixels | Used for |
|-------|--------|----------|
| `spacing.xs` | 4 | Compact UI, icon spacing, nested padding |
| `spacing.sm` | 8 | Tight layouts, button padding, inline gaps |
| `spacing.md` | 12 | Standard padding, card content, form fields |
| `spacing.lg` | 16 | Section spacing, modal padding, list gaps |
| `spacing.xl` | 24 | Page sections, card groups, form sections |
| `spacing.xxl` | 32 | Page margins, hero areas, major sections |

## Snap rules

| If value is | Snap to |
|-------------|---------|
| 0-6 | 4 (xs) |
| 7-10 | 8 (sm) |
| 11-14 | 12 (md) |
| 15-20 | 16 (lg) |
| 21-28 | 24 (xl) |
| 29+ | 32 (xxl) |
