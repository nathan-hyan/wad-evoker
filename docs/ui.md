# UI & Styling

## Aesthetic

Dark terminal / Doom-flavored. Blood red (`#cc2200`) accents, near-black backgrounds, `Courier New` monospace throughout.

- **All styles are inline QSS** (Qt StyleSheets) applied per-widget via `setStyleSheet()`
- No external style files or asset dependencies

### Color tokens (not yet extracted to variables — good first refactor)

| Role       | Values                          |
| ---------- | ------------------------------- |
| Background | `#141414`, `#111`, `#0d0d0d`    |
| Accent     | `#cc2200`, `#8b0000`, `#ff4422` |
| Text       | `#e8e0d0`, `#ccc`, `#666`       |
| Border     | `#2a2a2a`, `#3a3a3a`            |

---

## Shared Components

### `ui/styled_checkbox.py` — `StyledCheckBox`

A reusable `QCheckBox` subclass with a fully custom `paintEvent` that matches the app's dark terminal aesthetic. **Use this wherever a checkbox is needed in the UI instead of a plain `QCheckBox`.**

- **Unchecked**: dark `#1a1a1a` indicator box with `#3a3a3a` border
- **Checked**: blood-red `#8b0000` indicator with `#cc2200` border + centered white dash mark
- **Text**: always rendered in `#e8e0d0` using Courier New 11pt
- Sets its own font via `__init__` so `sizeHint()` is accurate without overriding it
- No QSS styles needed — all rendering is done in `paintEvent`

**Current uses**: `FilesLaunchDialog` (file checkboxes + "Don't ask" option), `WadEditDialog` (skip prompt toggle)
