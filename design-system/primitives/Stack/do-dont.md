# Stack — Do / Don't

## DO ✅

### Use Stack for vertical form layouts

```
✅ <Stack gap="lg"><Input /><Button /></Stack>
❌ Margin-bottom on each child element
```

### Use consistent gap across the page

```
✅ All vertical sections use spacing.lg
❌ Mixing spacing.sm, 13px, 1rem in the same view
```

## DON'T ❌

### Don't nest layout components unnecessarily

```
✅ <Stack gap="sm"><Text /><Text /></Stack>
❌ <Stack><Box><Inline><Text /></Inline></Box></Stack> (excessive nesting)
```
