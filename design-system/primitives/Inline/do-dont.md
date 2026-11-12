# Inline — Do / Don't

## DO ✅

### Use Inline for action groups

```
✅ <Inline gap="sm"><Button label="Save" /><Button label="Cancel" /></Inline>
❌ Float: left on each button
```

## DON'T ❌

### Don't nest layout components unnecessarily

```
✅ <Stack gap="sm"><Text /><Text /></Stack>
❌ <Stack><Box><Inline><Text /></Inline></Box></Stack> (excessive nesting)
```
