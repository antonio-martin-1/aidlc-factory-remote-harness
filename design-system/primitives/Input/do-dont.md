# Input — Do / Don't

## DO ✅

### Always associate labels with inputs

```
✅ <label for="email">Email</label><Input id="email" />
❌ Placeholder-only labels that disappear on input
```

### Show error messages inline

```
✅ <Input error="Email is required" /> with aria-describedby
❌ Alert banner at top of form
```

## DON'T ❌

### Don't use raw px values for spacing/padding

```
✅ style={{ padding: 'var(--spacing-md)' }}
❌ style={{ padding: '13px' }} → snaps to spacing.md (12px)
```
