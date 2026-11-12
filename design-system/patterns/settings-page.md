# Pattern: Settings Page

Composition of Stack + Surface + Input + Text for configuration UIs.

## Structure

```
Stack (gap="xl")
  ├── Text (variant="h2", "Settings")
  ├── Surface (level="level-1", padding="lg", radius="md")
  │   └── Stack (gap="md")
  │       ├── Text (variant="h4", "Section 1")
  │       └── Input (label="Setting 1")*
  ├── Surface (level="level-1", padding="lg", radius="md")
  │   └── Stack (gap="md")
  │       ├── Text (variant="h4", "Section 2")
  │       └── Input (label="Setting 2")*
  └── Inline (gap="sm")
       ├── Button (variant="primary", label="Save")
       └── Button (variant="ghost", label="Reset")
```

## Rules

1. Each section is a Surface card with heading
2. Max 8 fields per section card
3. Save/Reset buttons below last card
4. Cards separated by `spacing.xl` vertical gap
5. No border between sections (use spacing for separation)

## When to use

- User/application settings
- Configuration panels
- Preference screens

## When NOT to use

- Single-section form (< 8 fields) → use form-layout
- Wizard-style setup → use specialized wizard pattern
