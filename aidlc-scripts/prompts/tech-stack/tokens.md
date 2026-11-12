# Design Tokens — Code Generation Guidelines

## Token usage
CSS Custom Properties are available. Reference them via `var()`:
- Spacing: `var(--spacing-xs)` through `var(--spacing-xxl)`
- Radius: `var(--radius-none)` through `var(--radius-full)`
- Typography: `var(--typography-caption)` through `var(--typography-h1)`
- Colors: `var(--color-brand-*)`, `var(--color-neutral-*)`, `var(--color-semantic-*)`
- Elevation: `var(--elevation-*)` (where applicable)

## No raw values
❌ `padding: 13px` → ✅ `padding: var(--spacing-md)`
❌ `border-radius: 5px` → ✅ `border-radius: var(--radius-md)`
❌ `color: #2563EB` → ✅ `color: var(--color-brand-primary)`
❌ `font-size: 15px` → ✅ `font-size: var(--typography-body)`

## Tech stack
You are generating code for the project's detected tech stack.
Use framework conventions, components, and syntax idiomatic to that stack.
