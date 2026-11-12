# Icon — Do / Don't

## DO ✅

### Use consistent icon sizes within a context

```
✅ All toolbar icons are size="sm"
❌ Mixing sm, md, and lg icons in the same toolbar
```

## DON'T ❌

### Don't use color for decorative icons

```
✅ <Icon name="info" color={color.neutral.icon} />
❌ <Icon name="info" color="#FF0000" /> → use semantic.danger
```
