# Content Validation & Diagram Standards

## MANDATORY: Validate All Content Before File Creation

## ASCII Diagrams: Basic ASCII Only

**CRITICAL**: Max compatibility — use only `+` `-` `|` `^` `v` `<` `>` and alphanumeric text.

**FORBIDDEN**: Unicode box-drawing (`┌` `─` `│` `└` `┐` `┘` `├` `┤` `┬` `┴` `┼` `▼` `▲` `►` `◄`)

### Character Width Rule
**Every line in a box MUST have EXACTLY same character count (including spaces).**

### Patterns

**Box**: `+---+` top/bottom, `|   |` sides, `+` at corners
**Nested**: Indent inner boxes with consistent spacing
**Arrows**: `|` vertical, `-->` horizontal, `v` `^` direction markers
**Flow**: Chain boxes with arrows and optional labels

### Validation Checklist
- [ ] Basic ASCII only (`+` `-` `|` `^` `v` `<` `>`)
- [ ] No Unicode box-drawing
- [ ] Spaces (not tabs) for alignment
- [ ] ALL box lines same character width
- [ ] Corners align vertically in monospace font

## Mermaid Diagrams
1. Node IDs: alphanumeric + underscore only
2. Escape special chars in labels
3. Validate flowchart syntax
4. FALLBACK: If validation fails, use text-based representation
5. Always include text alternative alongside Mermaid

## General Content Validation
- Validate embedded code blocks (Mermaid, JSON, YAML)
- Check special character escaping
- Verify markdown syntax correctness
- Include fallback for complex elements
- If validation fails: log error, use fallback, don't block workflow, inform user
