# Pattern: Form Layout

Composition of Stack + Input + Button + Text for data entry forms.

## Structure

```
Stack (gap="lg")
  ├── Text (variant="h3")          — Form title
  ├── Stack (gap="md")             — Fields group
  │   ├── Input (label="Field 1")
  │   ├── Input (label="Field 2")
  │   └── ...
  ├── Inline (gap="sm")            — Actions row
  │   ├── Button (variant="primary", label="Submit")
  │   └── Button (variant="ghost", label="Cancel")
  └── Text (variant="caption")     — Optional help text
```

## Rules

1. Max 8 fields per form group. If >8, split into sections with headings.
2. Stack fields vertically — never horizontal field groups unless short (2 fields).
3. Submit button left-aligned (below fields), cancel button next to it.
4. Error messages appear below each field, not at top.
5. Loading state disables submit button, shows spinner.

## When to use

- Data entry forms (create, edit, settings)
- Search with filters (use Inline for filter row)

## When NOT to use

- Inline search (single field) → use Input directly
- Multi-step wizards → use specialized wizard pattern
