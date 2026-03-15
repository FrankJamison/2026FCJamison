# Accessibility / WCAG (Target: WCAG 2.2 AA)

This repo has been hardened toward WCAG compliance, but **formal conformance can’t be guaranteed by code changes alone** — it requires a combination of automated scans and manual testing evidence.

## What’s already implemented (high level)

- Semantic landmarks and headings (header/nav/main/footer patterns)
- Modal accessibility normalization (Bootstrap modal ARIA patterns like `aria-modal` + `aria-labelledby` targets)
- Icon-only controls have accessible names (e.g. `aria-label` on social links)
- Keyboard usability improvements for the mobile/off-canvas menu (Tab handling + Escape close + focus restore)
- Structured data in JSON-LD is valid JSON (SEO + some assistive-tech parsing friendliness)

## Automated checks (fast regression)

Run the lightweight template regression script:

```bash
python3 tools/a11y_sanity_check.py
```

This is intentionally a “cheap and cheerful” guardrail. It can catch common regressions like:

- icon-only links without accessible names
- missing `alt` attributes
- broken `aria-labelledby` references
- duplicate IDs

## Required manual checks (minimum)

Do these checks in a real browser (Chrome + Firefox recommended):

### Keyboard-only walkthrough

- Use Tab / Shift+Tab from the top of the page
- Verify the skip link works and moves focus into main content
- Open and close the mobile menu:
  - focus moves into the menu when opened
  - Tab stays inside while open (no “tabbing behind”)
  - Escape closes the menu
  - focus returns to the button/link that opened it
- Open and close a portfolio modal:
  - focus is trapped inside the modal while open
  - Escape closes
  - focus returns to the triggering button

### Visible focus

- Ensure every interactive element has a visible focus indicator

### Contrast

- Run a contrast checker (see tools below) and fix any failures to WCAG 2.2 AA contrast thresholds:
  - normal text: $\ge 4.5:1$
  - large text (≥ 24px regular or ≥ 18.66px bold): $\ge 3:1$

### Screen reader spot-check (basic)

- Confirm headings/landmarks make sense
- Confirm controls have meaningful names (especially icon-only links/buttons)
- Confirm modals announce their title and do not leak background content

## Suggested audit tools (pick 1–2)

- Chrome DevTools → Lighthouse (Accessibility)
- axe DevTools browser extension (Accessibility)
- WAVE browser extension (Accessibility)

## Evidence (recommended)

For a defensible “WCAG compliant” claim, save:

- Lighthouse report(s) for key pages
- axe/WAVE issue list(s) showing 0 serious/critical issues
- a short manual test note covering keyboard + focus + modals + contrast

A simple approach is to store these artifacts outside git, or in a private folder, depending on your workflow.
