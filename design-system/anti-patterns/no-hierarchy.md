# Anti-pattern: No Visual Hierarchy

**BAD**: Same font size and weight for headings and body text.

```tsx
// ❌ BAD — no hierarchy
<Text variant="body">Page Title</Text>
<Text variant="body">This is a description of the page content.</Text>
<Text variant="body">Section Heading</Text>
<Text variant="body">Another paragraph of content.</Text>
```

**GOOD**: Use appropriate variants to establish hierarchy.

```tsx
// ✅ GOOD — clear hierarchy
<Text variant="h2">Page Title</Text>
<Text variant="body">This is a description of the page content.</Text>
<Text variant="h4">Section Heading</Text>
<Text variant="body">Another paragraph of content.</Text>
```

## Why this is an anti-pattern

- Users scan pages visually — without hierarchy, everything looks the same
- No landmarks for skimming
- Accessibility: screen reader users lose navigation cues
- Makes important content indistinguishable from secondary content

## Hierarchy rules

1. One `h1` or `h2` per page (page title)
2. Section headings use `h3` or `h4`
3. Body content uses `body` (14px) or `body-large` (16px)
4. Secondary info uses `caption` (12px)
5. Never skip hierarchy levels (h2→h3, never h2→body→h2)
