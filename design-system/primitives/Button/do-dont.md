# Button — Do / Don't

## DO ✅

### Use primary variant for the main action

```
✅ <Button variant="primary" label="Save" />
❌ <Button variant="ghost" label="Save" />
```

### Use consistent height across related buttons

```
✅ Two buttons side-by-side, both same size="md"
❌ <Button size="sm" /> next to <Button size="lg" />
```

### Use `loading` state for async actions

```
✅ <Button variant="primary" label="Submit" loading={isSubmitting} />
❌ Manually disabling without spinner feedback
```

### Keep icon + label aligned

```
✅ <Button icon="plus" label="Add Item" />
❌ <Button label="Add Item" /><Icon name="plus" /> (separate elements)
```

**Button should contain the icon — not sit next to it**

## DON'T ❌

### Don't stack multiple primary buttons

```
✅ Use primary + secondary pair
❌ Two primary buttons competing for attention
```

### Don't use hardcoded padding

```
✅ (uses design tokens)
❌ style={{ padding: '7px 14px' }}  →  snaps to spacing.sm + spacing.md
```

### Don't use non-interactive elements as buttons

```
✅ <button> or <Button>
❌ <div onClick={...}> — no keyboard support, no role
❌ <span onClick={...}> — same issues
```

### Don't skip aria-label on icon buttons

```
✅ <Button variant="icon" icon="trash" aria-label="Delete item" />
❌ <Button variant="icon" icon="trash" />  — screen reader sees nothing
```

### Don't mix border-radius values on a page

```
✅ All buttons use radius.sm (3px)
❌ Some buttons 3px, others 6px, some 4px
```
