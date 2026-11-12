# Anti-pattern: Giant Forms

**BAD**: Single-column forms with >8 fields and no grouping.

```tsx
// ❌ BAD — 12 fields in one stack, no grouping
<Stack gap="md">
  <Input label="Username" />
  <Input label="First Name" />
  <Input label="Last Name" />
  <Input label="Email" />
  <Input label="Password" />
  <Input label="Confirm Password" />
  <Input label="Address Line 1" />
  <Input label="Address Line 2" />
  <Input label="City" />
  <Input label="State" />
  <Input label="ZIP Code" />
  <Input label="Phone" />
  <Button label="Submit" />
</Stack>
```

**GOOD**: Group related fields into sections.

```tsx
// ✅ GOOD — grouped into logical sections
<Stack gap="lg">
  <Surface padding="lg" radius="md">
    <Stack gap="md">
      <Text variant="h4">Account</Text>
      <Input label="Username" />
      <Input label="Email" />
      <Input label="Password" />
    </Stack>
  </Surface>
  <Surface padding="lg" radius="md">
    <Stack gap="md">
      <Text variant="h4">Personal Info</Text>
      <Inline gap="md">
        <Input label="First Name" />
        <Input label="Last Name" />
      </Inline>
      <Input label="Phone" />
    </Stack>
  </Surface>
  <Surface padding="lg" radius="md">
    <Stack gap="md">
      <Text variant="h4">Address</Text>
      <Input label="Address Line 1" />
      <Input label="City" />
      <Inline gap="md">
        <Input label="State" />
        <Input label="ZIP Code" />
      </Inline>
    </Stack>
  </Surface>
  <Button variant="primary" label="Save" />
</Stack>
```

## Why this is an anti-pattern

- Cognitive overload: users feel overwhelmed by long, unbroken form lists
- Higher abandonment rate for long forms
- Harder to scan and understand the form's structure
- Mobile: forces excessive scrolling

## Rules

- Max 8 fields per section (Surface card)
- Split >8 fields into logical sections with headings
- Use 2-column Inline for related short fields (city/state, first/last name)
- Each section should answer one question ("What's your address?")
