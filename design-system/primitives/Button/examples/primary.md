# Button — Example: Primary

```tsx
import { Button } from './components/Button';

function SaveForm() {
  return (
    <Button
      variant="primary"
      size="md"
      label="Save Changes"
      icon="check"
      onClick={handleSave}
    />
  );
}
```

# Button — Example: Secondary + Icon

```tsx
<Button
  variant="secondary"
  size="sm"
  label="Cancel"
  onClick={handleCancel}
/>
<Button
  variant="ghost"
  size="sm"
  icon="download"
  label="Export"
  onClick={handleExport}
/>
```

# Button — Example: Icon-only

```tsx
<Button
  variant="icon"
  size="md"
  icon="trash"
  aria-label="Delete item"
  onClick={handleDelete}
/>
```

# Button — Example: Loading state

```tsx
function SubmitForm() {
  const [loading, setLoading] = useState(false);

  return (
    <Button
      variant="primary"
      size="lg"
      label={loading ? 'Saving...' : 'Submit'}
      loading={loading}
      onClick={async () => {
        setLoading(true);
        await submit();
        setLoading(false);
      }}
    />
  );
}
```

# Button — Example: Danger + Confirmation

```tsx
<Button
  variant="danger"
  size="md"
  label="Delete Account"
  icon="warning"
  onClick={() => confirm('Are you sure?') && handleDelete()}
/>
```
