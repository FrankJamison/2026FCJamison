# Accessibility Standard and Verification Runbook

This document defines the production accessibility standard for this repository.

## 1. Accessibility policy

Target conformance:

- WCAG 2.2 Level AA

Scope:

- Server-rendered pages and partials under templates/
- Interactive UI in static/js/main.js
- Form flows: /contact and /leave-reply
- Modal workflows and mobile/off-canvas navigation

Conformance statement:

- Accessibility is treated as a release quality gate, not a best-effort enhancement.
- No release should introduce new critical accessibility failures.

## 2. Repository baseline

This codebase already includes core accessibility patterns:

- Skip link to main content
- Landmark and semantic structure (header/nav/main/footer)
- Accessible names for icon-only controls
- Modal title association via aria-labelledby
- Keyboard support for menu and modal interactions (including Escape)

Known implementation guardrail:

- Automated template checks are available via tools/a11y_sanity_check.py

## 3. Standards and acceptance criteria

### Keyboard and focus

- Every interactive control must be operable with keyboard only.
- Focus must be visible on all interactive controls.
- Focus order must be logical and follow visual reading order.
- Modal and off-canvas patterns must contain focus while open and return focus to invoker when closed.

### Naming and semantics

- All form controls must have accessible labels.
- Icon-only links/buttons must expose accessible names (aria-label or equivalent).
- Headings must be hierarchical and descriptive.
- Landmark roles/regions must be meaningful and non-duplicative.

### Non-text content

- All informative images require accurate alt text.
- Decorative images should use empty alt text.
- No image may ship without explicit alt handling.

### Color and perception

- Normal text contrast must be at least 4.5:1.
- Large text contrast must be at least 3:1.
- Focus indicators and UI states must remain perceivable in high contrast scenarios.

### Forms and errors

- Validation errors must be perceivable, specific, and programmatically associated where possible.
- Required fields must be communicated without relying only on color.

## 4. Automated testing requirements

### Mandatory regression check

Run before every release:

```bash
python3 tools/a11y_sanity_check.py
```

This script checks for high-signal template regressions:

- Missing alt attributes
- Missing aria-labelledby targets
- Duplicate IDs
- Icon-only links without accessible names

### Recommended automated audits

Use at least one page-level scanner per release candidate:

- axe DevTools browser extension
- Lighthouse accessibility audit
- WAVE browser extension

Release threshold recommendation:

- 0 critical issues
- 0 serious issues
- Any remaining moderate/minor items documented with remediation ETA

## 5. Manual test protocol (required)

Execute these checks on release candidates in Chrome and Firefox at minimum.

### Keyboard walkthrough

1. Start at top of page and tab through all controls.
2. Confirm skip link moves focus to main content.
3. Open mobile menu and verify:
   - Focus enters menu.
   - Focus does not escape menu while open.
   - Escape closes menu.
   - Focus returns to opener.
4. Open project modals and verify:
   - Title is announced and associated.
   - Focus remains within modal while open.
   - Escape closes modal.
   - Focus returns to invoking element.

### Screen reader spot checks

Perform lightweight checks with one desktop screen reader:

- Windows: NVDA or JAWS
- macOS: VoiceOver

Checks:

- Heading navigation is coherent.
- Landmarks are meaningful.
- Form controls and status/error messages are announced clearly.

### Zoom and reflow

- Verify usability at 200% zoom without loss of functionality.
- Confirm no critical content/functionality requires horizontal scrolling at common viewport widths.

## 6. Test evidence and release gate

For each production release, retain:

- Output from tools/a11y_sanity_check.py
- Scanner results (axe/Lighthouse/WAVE)
- Manual test notes (keyboard + modal + mobile menu + forms)
- List of open a11y defects and risk classification

Release gate:

- Block release on new critical or serious accessibility defects.
- If exception is required, document owner, rationale, user impact, mitigation, and due date.

## 7. Defect severity and SLA guidance

Use these severities for triage:

- Critical: blocks task completion for assistive technology users
- High: major friction or substantial loss of functionality
- Medium: partial friction with workaround available
- Low: cosmetic or non-blocking standards deviation

Recommended remediation targets:

- Critical: fix before release
- High: fix within 7 days
- Medium: fix within 30 days
- Low: fix in planned backlog

## 8. Engineering guidelines for future changes

- Prefer native HTML semantics before ARIA.
- Avoid custom widgets where native controls are sufficient.
- Keep interactive state synchronized between DOM, ARIA, and keyboard behavior.
- Validate every new component with keyboard and screen reader checks before merge.
- Treat accessible naming and focus logic as part of component definition of done.

## 9. Operational checks in production

After deployment, re-run quick checks in live environment:

1. Homepage keyboard path and skip link
2. Mobile menu open/close/focus restoration
3. Portfolio modal focus containment and close behavior
4. Contact and leave-reply form error/success messaging

If production-only regressions are detected, roll forward with a hotfix or rollback per production runbook.

## 10. Ownership

- Engineering owns implementation and regression prevention.
- QA/release owner owns verification evidence per release.
- Product owner approves any temporary accessibility exception with due date.

Accessibility is a continuous quality obligation, not a one-time milestone.
