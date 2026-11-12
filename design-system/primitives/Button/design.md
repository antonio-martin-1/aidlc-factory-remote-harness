# Button

Primary action trigger. Clickable element that initiates an action.

## Constraints

| Property | Value | Notes |
|----------|-------|-------|
| Height (sm) | 28px | Compact, used in toolbars/tables |
| Height (md) | 36px | Default size |
| Height (lg) | 44px | Touch-friendly, mobile |
| Border radius | `radius.sm` (3px) | — |
| Font size | `font-size.body` (14px) | — |
| Font weight | `font-weight.medium` (500) | — |
| Padding horizontal (sm) | `spacing.md` (12px) | — |
| Padding horizontal (md/lg) | `spacing.lg` (16px) | — |
| Vertical padding | `spacing.xs` (4px) sm, `spacing.sm` (8px) md/lg | Centered text |

## Variants

| Variant | Purpose | BG | Text | Border |
|---------|---------|----|------|--------|
| `primary` | Main CTA | `color.brand.primary` | White | None |
| `secondary` | Alternative | Transparent | `color.brand.primary` | `color.brand.primary` |
| `ghost` | Low emphasis | Transparent | `color.neutral.text-primary` | None |
| `danger` | Destructive | `color.semantic.danger` | White | None |
| `icon` | Icon-only | Transparent | `color.neutral.icon` | None |

## Sizes

| Size | Height | Padding X | Padding Y | Font |
|------|--------|-----------|-----------|------|
| `sm` | 28px | `spacing.md` | `spacing.xs` | 14px |
| `md` | 36px | `spacing.lg` | `spacing.sm` | 14px |
| `lg` | 44px | `spacing.lg` | `spacing.sm` | 16px |

## Interactions

| State | Behavior |
|-------|----------|
| Default | Normal variant colors |
| Hover | BG darkens 10%, cursor: pointer |
| Active/Pressed | BG darkens 20% |
| Disabled | Opacity 0.5, cursor: not-allowed, no hover effect |
| Focus | `color.brand.primary` outline/focus-ring |

## Accessibility

- Must have visible focus ring
- Must have `aria-label` when icon-only
- Must have `disabled` attribute (not just CSS class)
- Must support keyboard (Enter/Space activation)
- Minimum touch target 44x44px (lg) or surrounding padding

## When NOT to use

- Navigation between pages → use `<a>` / `Link` component
- Non-action decorative elements → use `Text` or `Icon`
- Multiple primary buttons on one view → max one primary, rest secondary/ghost
- Triggering in-page navigation/tabs → use tab component or `<a>`
