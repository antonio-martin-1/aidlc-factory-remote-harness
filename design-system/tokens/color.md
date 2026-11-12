# Color Tokens

Semantic color tokens. Always reference these — never use raw hex values.

## Brand

| Token | Hex | Used for |
|-------|-----|----------|
| `color.brand.primary` | #2563EB | Primary buttons, links, active states |
| `color.brand.primary-hover` | #1D4ED8 | Primary button hover |
| `color.brand.secondary` | #6366F1 | Secondary accents |
| `color.brand.secondary-hover` | #4F46E5 | Secondary accent hover |

## Neutral

| Token | Hex | Used for |
|-------|-----|----------|
| `color.neutral.bg` | #FFFFFF | Page backgrounds, surfaces |
| `color.neutral.surface` | #F9FAFB | Card/panel backgrounds |
| `color.neutral.border` | #E5E7EB | Borders, dividers |
| `color.neutral.text-primary` | #111827 | Primary text, headings |
| `color.neutral.text-secondary` | #6B7280 | Secondary text, labels |
| `color.neutral.text-disabled` | #9CA3AF | Disabled text |
| `color.neutral.icon` | #6B7280 | UI icons |

## Semantic

| Token | Hex | Used for |
|-------|-----|----------|
| `color.semantic.success` | #10B981 | Success states, positive feedback |
| `color.semantic.warning` | #F59E0B | Warning states, caution |
| `color.semantic.danger` | #EF4444 | Errors, destructive actions |
| `color.semantic.info` | #3B82F6 | Informational states |
| `color.semantic.danger-bg` | #FEF2F2 | Error background, alert surfaces |
| `color.semantic.success-bg` | #F0FDF4 | Success background |

## Overlay

| Token | Value | Used for |
|-------|-------|----------|
| `color.overlay.dark` | rgba(0,0,0,0.5) | Modal backdrops |
| `color.overlay.light` | rgba(0,0,0,0.08) | Hover states, focus rings |

## Run accent

`color.brand.primary` (`#2563EB`) and `color.brand.secondary` (`#6366F1`) are the fallback palette. They are the generic blue and indigo, and a product that keeps them will look like every other generated screen.

When `aidlc-docs/inception/design-pass/<run-id>-design-direction.md` sets `Accent status: approved`, that hex replaces `color.brand.primary` for the run. Write it here and in `tokens.css` as `--color-brand.primary`. Components reference the token. An unapproved accent stays on this fallback.

## Snap rules

| If raw hex matches | Replace with |
|--------------------|--------------|
| #1D4ED8, #1E40AF, any blue-700+ | `color.brand.primary` |
| #EF4444, #DC2626, #B91C1C | `color.semantic.danger` or `color.semantic.danger-bg` |
| #10B981, #059669, #047857 | `color.semantic.success` |
| #F59E0B, #D97706 | `color.semantic.warning` |
| #111827, #1F2937, #374151 | `color.neutral.text-primary` |
| #6B7280, #9CA3AF | `color.neutral.text-secondary` |
