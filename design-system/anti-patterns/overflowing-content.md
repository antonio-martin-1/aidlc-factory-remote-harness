# Anti-pattern: Overflowing Content

**BAD**: Fixed heights without overflow handling.

```tsx
// ❌ BAD — fixed height, content clipped
<div style={{ height: '200px' }}>
  <LongContent /> {/* clipped if taller than 200px */}
</div>
```

**GOOD**: Let content determine height, or handle overflow explicitly.

```tsx
// ✅ GOOD — min-height or overflow handling
<Box style={{ minHeight: '200px' }}>
  <LongContent /> {/* grows naturally */}
</Box>

// ✅ GOOD — scroll when needed
<Box style={{ height: '400px', overflowY: 'auto' }}>
  <ScrollableContent />
</Box>
```

## Why this is an anti-pattern

- Content changes break layout silently
- Users can't see or scroll to hidden content
- Breaks with translations (longer text)
- Accessibility issue — screen readers may not detect clipped content

## Rule

- Prefer `min-height` over `height` for containers with dynamic content
- If fixed height is required, MUST add `overflow: auto` or `overflow-y: auto`
- Never use `overflow: hidden` on content containers (only on decorative elements)
