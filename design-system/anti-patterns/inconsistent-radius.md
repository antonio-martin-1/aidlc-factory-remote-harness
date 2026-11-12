# Anti-pattern: Inconsistent Border Radius

**BAD**: Mixing different radius values on similar elements within the same view.

```css
/* ❌ BAD — three different radii on similar components */
.btn-primary { border-radius: 3px; }
.card { border-radius: 8px; }
.input-field { border-radius: 4px; }
```

**GOOD**: Consistent radius per element type, from `tokens/radius.md`.

```css
/* ✅ GOOD — consistent token usage */
.btn-primary { border-radius: 3px; }   /* radius.sm */
.btn-secondary { border-radius: 3px; } /* radius.sm — same! */
.card { border-radius: 6px; }          /* radius.md */
.input-field { border-radius: 3px; }   /* radius.sm */
```

## Why this is an anti-pattern

- Users perceive inconsistent rounding as sloppy
- 4px doesn't match any canonical token (0, 3, 6, 12, 9999)
- 8px is close to md (6px) but not exact
- Makes the UI look uncoordinated

## Rule of thumb

- Interactive elements (buttons, inputs): `radius.sm` (3px)
- Containers (cards, modals): `radius.md` (6px)
- Large overlays (dialogs): `radius.lg` (12px)
- Pills/avatars: `radius.full` (9999px)
- Never mix >2 radius values on one page
