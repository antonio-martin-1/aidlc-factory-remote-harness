# Pattern: Modal Dialog

Composition of Surface + Stack + Button + Text for overlay dialogs.

## Structure

```
<div class="modal-backdrop">       — color.overlay.dark, z.modal
  └── Surface (level="level-1", elevation="lg", radius="lg")
       └── Stack (gap="md")
            ├── Inline (gap="sm")
            │   ├── Text (variant="h4")
            │   ├── (spacer)
            │   └── Button (variant="icon", icon="x", aria-label="Close")
            ├── Text (variant="body")        — Content
            └── Inline (gap="sm")
                 ├── Button (variant="primary", label="Confirm")
                 └── Button (variant="ghost", label="Cancel")
```

## Rules

1. Backdrop is always `color.overlay.dark`, click closes modal
2. Width: 480px (default), max 90vw
3. Close button always present (X top-right)
4. Escape key closes modal
5. Focus trap: Tab cycles within modal only
6. Scroll lock on body when open

## When to use

- Confirmations before destructive actions
- Forms that need focus (short forms only)
- Alerts and notices

## When NOT to use

- Long content → use a page/section instead
- > 5 fields in a form → use a page
- Notifications → use toast pattern
