---
name: browser-testing-with-devtools
description: Browser automation and testing via Chrome DevTools Protocol for UI testing, screenshot diffing, network interception, and Lighthouse audits. Used by build-test-agent when project_profile.ui == true.
---

# Browser Testing with DevTools

Browser-level testing using Chrome DevTools Protocol tools (snapshot, click, fill, screenshot, network, lighthouse).

## Why this skill exists

UI test failures are often invisible to headless CI — a button is off-screen, an API call returns 500, a font fails to load. DevTools introspect exactly what the browser sees.

## Process

1. **Snapshot the page** — `chrome-devtools_take_snapshot` to get the a11y tree
2. **Click elements** — `chrome-devtools_click` with `uid` from snapshot
3. **Fill forms** — `chrome-devtools_fill` or `chrome-devtools_fill_form` for inputs
4. **Take screenshot** — `chrome-devtools_take_screenshot` for visual comparison
5. **Inspect network** — `chrome-devtools_list_network_requests` + `chrome-devtools_get_network_request` for API monitoring
6. **Audit** — `chrome-devtools_lighthouse_audit` for perf/a11y score regression
7. **Check console** — `chrome-devtools_list_console_messages` for runtime errors

## Verification

- Screenshot saved and visually verified
- No console errors of severity `error` or higher
- Lighthouse score within 5% of baseline
- Network requests all return 2xx/3xx

## Common Rationalizations

| Rationalization | Why it fails |
|---|---|
| "Tests pass in Jest/DOM" | JSDOM doesn't run real layout/network |
| "It renders fine for me" | Browser, screen size, and device differences matter |
| "E2E tests are too slow" | DevTools snapshot/click/fill takes <500ms per interaction |
