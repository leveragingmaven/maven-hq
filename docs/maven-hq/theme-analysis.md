# Theme & Branding Architecture Analysis

## 1. Theme Architecture

### 1.1 Theme Provider

The theme system lives entirely in `static/js/theme.js` (~2115 lines). There is no formal provider/consumer pattern — it is a flat module that reads/writes CSS custom properties directly on `document.documentElement`.

**Startup sequence:**

| Step | File | What Happens |
|---|---|---|
| 1 | `static/index.html` (inline `<head>` script, lines 16–100) | Synchronously reads `localStorage` theme before first paint. Sets all CSS variables, meta theme-color, and favicon. Provides zero-flash first paint. |
| 2 | `static/index.html` (inline `<head>` script, lines 105–196) | Reads theme again. Sets per-route favicon SVG + PWA manifest Blob + `<title>`. |
| 3 | `static/js/theme.js` module auto-init (lines 2083–2115) | Loads server-persisted themes, merges with local, initializes theme UI, calls `applyColors()`. |

### 1.2 CSS Architecture

**Single monolithic file:** `static/style.css` — 39,571 lines / 1.3 MB. No imports, no preprocessor. No secondary CSS files.

**Naming convention:** Modified BEM-like with hyphenated component prefixes (`.sidebar-header`, `.modal-content`, `.chat-input-bar`). State classes on `<body>` (`.welcome-ready`, `.notes-view`).

### 1.3 CSS Variable System

**~108 unique CSS custom properties** organized in layers:

| Layer | Variables | Source |
|---|---|---|
| `:root` (dark) | `--bg`, `--fg`, `--panel`, `--border`, `--red`, `--green`, `--warn`, syntax highlight colors, semantic colors | `style.css:18-69` |
| `:root.light` (light override) | ~20 overrides of the above | `style.css:71-91` |
| Runtime (JS-set) | `--accent`, `--brand-color`, `--sidebar-bg`, `--hamburger-color`, `--user-bubble-bg`, `--send-btn-bg`, `--code-bg`, `--toggle-active`, etc. | `theme.js` |
| Layout (JS-set) | `--sidebar-w`, `--icon-rail-w`, `--left-dock-w`, `--right-dock-w`, `--composer-clearance` | `sidebar-layout.js`, `tileManager.js` |
| Scoped | Component-specific vars like `--cat-hue`, `--swatch-color`, `--ctx-color` | Various inline scopes |

**Fallback chains** are used extensively: `var(--accent, var(--red))`, `var(--font-family, 'Fira Code', monospace)`, `var(--sidebar-bg, var(--panel))`.

### 1.4 Theme Switching

`applyColors(colors)` in `theme.js:257` modifies:

1. Root CSS variables (`--bg`, `--fg`, `--panel`, `--border`, `--red`)
2. `<meta name="theme-color">` content
3. Syntax highlight variables (computed from base colors)
4. 14 advanced CSS variables (computed defaults or user overrides)
5. Favicon SVG data URI (recolored with accent)

### 1.5 Theme Persistence

| Storage | Key | What |
|---|---|---|
| `localStorage` | `'odysseus-theme'` | Active theme object |
| `localStorage` | `'odysseus-custom-themes'` | Custom themes (max 8) |
| Server | `PUT /api/prefs/theme` | Active theme sync |
| Server | `PUT /api/prefs/custom-themes` | Custom themes sync |

### 1.6 19 Built-in Themes

dark, light, midnight, paper, cyberpunk, retrowave, forest, ocean, ume, copper, terminal, organs, lavender, gpt, claude, cute + 3 default presets. Each defined as `{ bg, fg, panel, border, red }`. No formal light/dark pairing — light/dark determined dynamically by HSL lightness.

---

## 2. Branding System — Complete Inventory

### 2.1 Brand Name: "Odysseus"

| Location | File | Line |
|---|---|---|
| Browser `<title>` | `static/index.html` | 5, 158–167 |
| Login `<title>` | `static/login.html` | 6 |
| Docs `<title>` | `docs/index.html` | 7 |
| PWA manifest name | `static/manifest.json` | 2–3 |
| Sidebar brand | `static/index.html` | 709 |
| Welcome screen | `static/index.html` | 960 |
| Settings label | `static/index.html` | 514, 1728 |
| Theme label | `static/js/theme.js` | 187 |
| Login page logo | `static/login.html` | 256 |
| AIO hidden heading | `static/index.html` | 955 |
| Chat meta | `static/index.html` | 958 |
| Splash window | `launcher.py` | 42, 56 |
| System tray | `launcher.py` | 98, 102, 104 |
| PyInstaller spec | `Odysseus.spec` | 24, 44 |
| Service worker | `static/sw.js` | 1, 10 |
| Session cookie | `routes/auth_routes.py` | 84 |
| TOTP issuer | `core/auth.py` | 509 |
| Internal headers | `app.py`, `core/middleware.py`, `routes/email_routes.py` | Multiple |
| Env vars | `app.py` (ODYSSEUS_*) | Multiple |
| Backup filename | `routes/backup_routes.py` | 55 |
| Cache name | `static/sw.js` | 10 |

### 2.2 Logo (Sailboat SVG)

| Location | Type | File | Line |
|---|---|---|---|
| Static favicon | Inline data URI SVG | `static/index.html` | 6 |
| Dynamic favicon template | JS string with color subst | `static/index.html` | 42–43 |
| Static favicon | Inline data URI SVG | `static/login.html` | 7 |
| Login page logo | Inline `<svg>` | `static/login.html` | 256 |
| Welcome screen | Inline `<svg>` | `static/index.html` | 960 |
| PWA per-route manifest | Blob URL with SVG | `static/index.html` | 176–192 |
| Theme favicon fallback | JS string | `static/js/theme.js` | 339, 343–346 |
| Docs static favicon | Inline data URI SVG | `docs/index.html` | 8 |
| Docs hero logo | Inline `<svg>` | `docs/index.html` | 404, 425 |
| System tray | Pillow-drawn polygon | `launcher.py` | 74–80 |
| PyInstaller icon | `static/icon.ico` | `Odysseus.spec` | 35 |

### 2.3 Favicon

| Implementation | File | Format |
|---|---|---|
| Static inline SVG | `static/index.html:6`, `static/login.html:7`, `docs/index.html:8` | data:image/svg+xml |
| Dynamic per-route | `static/index.html:40-43`, `theme.js:290-357` | data:image/svg+xml (recolored) |
| Fallback ICO | `static/icon.ico` | .ico |
| PWA icons | `static/icons/icon-{192,512,maskable-512}.png` | PNG |
| Notification icons | JS references `/static/favicon.ico` and `/static/favicon.png` (files do not exist) | Reference only |

### 2.4 Fonts

| Family | Weights | Files | Declared In |
|---|---|---|---|
| Fira Code | 300, 400, 600 | `static/fonts/FiraCode-*.woff2` | `style.css:113-115`, `style.css:7954-7956` (duplicate), `login.html:88-89` |
| Inter | 400, 500, 600 | `static/fonts/Inter-*.woff2` | `index.html:201-203` |
| OpenDyslexic | 400, 700 | `static/fonts/OpenDyslexic-*.woff2` | `style.css:118-119` |
| Custom fonts | User-added | `static/fonts/custom/` | Dynamic `@font-face` injection |

**Default font stack:** `var(--font-family, 'Fira Code', monospace)`. UI components like `.modal-content` override with Inter sans-serif.

### 2.5 Color System

The core brand palette of the existing app:

| Role | Dark Default | Light Default |
|---|---|---|
| Background (`--bg`) | `#282c34` | `#f5f5f5` |
| Text (`--fg`) | `#9cdef2` | `#2b2b2b` |
| Panel (`--panel`) | `#111` | `#fff` |
| Border (`--border`) | `#355a66` | `#bbb` |
| Accent (`--red`) | `#e06c75` | `#e06c75` |

All 19 themes override these 5 core colors. All other visual colors are derived from these 5 via `color-mix()`, `deriveSyntaxColors()`, and `computeAdvancedDefaults()`.

### 2.6 Icons

**100% inline SVGs.** No icon libraries. All sidebar, rail, and tool icons are hand-authored `<svg>` elements using `stroke="currentColor"` and `width="14-16"`.

### 2.7 Loading Screens

| Screen | Location | Implementation |
|---|---|---|
| App loader | `static/index.html:232-248` | Full-screen overlay, ASCII wave animation, 5s timeout |
| Python splash | `launcher.py:38-63` | tkinter frameless window, "⛵ Odysseus" text |
| Login spinner | `static/login.html:241-250` | CSS whirlpool in submit button |
| Welcome animation | `static/style.css:23417-23444` | CSS clip-path reveal on `.welcome-name` |

---

## 3. Customization Points

### 3.1 Files That Must Be Modified for Rebranding

| File | What to Change | Classification |
|---|---|---|
| `static/manifest.json` | PWA name, description, icons | **Required** |
| `static/index.html` | `<title>`, route titles, sidebar brand text, welcome text, chat meta text, settings labels, AIO heading, favicon SVG data URI | **Required** |
| `static/login.html` | `<title>`, logo SVG, brand text, favicon SVG data URI | **Required** |
| `static/js/theme.js` | `ADV_KEYS` brand color label, theme accent defaults, favicon fallback SVG | **Required** |
| `static/sw.js` | Cache name, service worker banner comment | **Required** |
| `launcher.py` | Window title, splash text, tray icon name/tooltip, tray icon drawing | **Required** |
| `Odysseus.spec` | EXE name, .spec filename | **Required** |
| `docs/index.html` | `<title>`, favicon SVGs, logo SVGs, brand text | **Required** |
| `static/icons/icon-192.png` | Replace with Maven HQ icon (192×192) | **Required** |
| `static/icons/icon-512.png` | Replace with Maven HQ icon (512×512) | **Required** |
| `static/icons/icon-maskable-512.png` | Replace with Maven HQ maskable icon (512×512) | **Required** |
| `static/icon.ico` | Replace with Maven HQ .ico file | **Required** |

### 3.2 Files That Should Be Modified (Strongly Recommended)

| File | What to Change | Classification |
|---|---|---|
| `static/style.css` | `:root` variable defaults (accent, bg, fg, panel, border, semantic colors) | **Recommended** |
| `routes/auth_routes.py` | Session cookie name (`odysseus_session`) | **Recommended** |
| `core/auth.py` | TOTP issuer name | **Recommended** |
| `routes/backup_routes.py` | Backup filename prefix | **Recommended** |
| `core/middleware.py` | Internal header names, env var names | **Recommended** |
| `app.py` | Env var names (`ODYSSEUS_*`), internal header names | **Recommended** |
| `routes/email_routes.py` | Header names (`X-Odysseus-*`) | **Recommended** |
| `docs/odysseus-wordmark.png` | Replace with Maven HQ wordmark | **Recommended** |
| `docs/odysseus.jpg` | Replace with Maven HQ screenshot | **Recommended** |
| `docs/odysseus-browser.jpg` | Replace with Maven HQ browser shot | **Recommended** |

### 3.3 Files That Should NOT Be Modified

| File | Rationale | Classification |
|---|---|---|
| `static/style.css` (body of file, not root vars) | Component styles are upstream. Changing them introduces merge conflicts. Override via CSS variables instead. | **Leave As-Is** |
| `static/js/` (most modules) | Core application logic. Branding should not touch business logic. | **Leave As-Is** |
| `static/app.js` | Event wiring, initialization. No branding content. | **Leave As-Is** |
| `routes/*.py` (except auth/backup/email) | API endpoints. No branding. | **Leave As-Is** |
| `core/database.py`, `core/constants.py` | Data layer. No branding. | **Leave As-Is** |
| `src/` | Backend logic. No branding. | **Leave As-Is** |
| `companion/` | Companion bridge. Internal only. | **Leave As-Is** |
| `static/fonts/` (font files) | Fonts are functional assets. Keep unless changing brand font. | **Leave As-Is** |
| `static/js/providers.js` | Third-party provider logos. Not app branding. | **Leave As-Is** |
| `static/icons/ollama-mark.png`, `sglang-*.png` | Third-party provider logos. Not app branding. | **Leave As-Is** |

### 3.4 Assets That Must Be Replaced

| Asset | Replace With |
|---|---|
| Sailboat SVG (all inline occurrences) | Maven HQ logo SVG |
| `static/icon.ico` | Maven HQ `.ico` |
| `static/icons/icon-192.png` | Maven HQ 192×192 PNG |
| `static/icons/icon-512.png` | Maven HQ 512×512 PNG |
| `static/icons/icon-maskable-512.png` | Maven HQ maskable 512×512 PNG |
| `docs/odysseus-wordmark.png` | Maven HQ wordmark |
| `docs/odysseus.jpg` | Maven HQ screenshot |
| `docs/odysseus-browser.jpg` | Maven HQ browser shot |

### 3.5 Assets That Should Remain Unchanged

| Asset | Rationale |
|---|---|
| `static/fonts/FiraCode-*.woff2` | Functional font. Keep unless changing brand font. |
| `static/fonts/Inter-*.woff2` | Functional font. Keep unless changing brand font. |
| `static/fonts/OpenDyslexic-*.woff2` | Accessibility font. Keep. |
| `static/js/providers.js` SVG logos | Third-party provider logos. Not app branding. |
| `static/icons/ollama-*.png`, `sglang-*.png` | Third-party provider logos. Not app branding. |
| `docs/*.webm` | Product demo videos. Not branding. |

---

## 4. Centralized Branding Layer Analysis

### 4.1 Candidate for Centralization: Brand Name

**Current state:** Hardcoded as `"Odysseus"` in ~30+ locations across HTML, JS, Python, and config files.

**Could a single variable replace all occurrences?**

| Location Type | Count | Centralizable? |
|---|---|---|
| `<title>` tags | 3 files | **Partially.** Can use JS to set `document.title`, but the static fallback in `<title>` must exist for SEO/pre-render. |
| `manifest.json` | 1 file | **No.** Manifest is a static JSON file. Would need a build step or server-side template. |
| Inline HTML text | ~12 locations | **Yes.** JS could query a config object and set textContent on DOM elements. |
| `launcher.py` | 4 locations | **No.** Python string literals. Would need a config constant. |
| `Odysseus.spec` | 2 locations | **No.** PyInstaller config file. |
| Backend headers/env vars | ~10 locations | **No.** Python constants. Would need a branding config module. |
| `theme.js` labels | 2 locations | **Yes.** JS string constant. |

**Verdict:** Partial centralization possible for frontend text surfaces. Backend and config files must remain hardcoded.

### 4.2 Candidate for Centralization: Logo

**Current state:** Sailboat SVG duplicated as inline markup in 3 HTML files + 2 JS files + 1 Python file (Pillow drawing).

**Could a single SVG file replace all occurrences?**

| Use Case | Centralizable? |
|---|---|
| Inline data URI favicon | **Yes.** Reference a shared SVG template in `theme.js` or a global JS constant. |
| Login page logo | **Yes.** Reference same template. |
| Welcome screen logo | **Yes.** Reference same template. |
| System tray icon (Pillow) | **No.** Must draw programmatically with Pillow polygons. Would need separate implementation. |
| PWA manifest icon (Blob URL) | **Yes.** Already uses JS-generated URLs. |

**Verdict:** A single JS constant holding the logo SVG markup can serve all frontend uses. Python tray icon needs separate handling.

### 4.3 Candidate for Centralization: Color Palette

**Current state:** 5 base colors per theme (bg, fg, panel, border, red) defined in `theme.js` as JS objects. These drive CSS variables which propagate everywhere.

**Can a single palette definition serve all needs?**

| Variable | Already Centralized? | Notes |
|---|---|---|
| `--red` (accent) | **Yes.** Defined per-theme in `theme.js`, set as CSS variable at runtime. | Already excellent. |
| `--bg`, `--fg`, `--panel`, `--border` | **Yes.** Same as above. | Already excellent. |
| `--brand-color` | **Yes.** Overridable per-theme, computed default is `colors.red`. | Perfect for branding. |
| Semantic colors (`--color-error`, `--color-success`) | **Partial.** Defined in `style.css:root` but overridable via JS. | Could add to `ADV_KEYS` for full centralization. |

**Verdict:** The color system is already highly centralized. The `--brand-color` variable is the ideal single point of control for the Maven HQ brand accent.

### 4.4 Candidate for Centralization: Icons

**Current state:** 100% inline SVGs, each hand-authored in the HTML.

**Could a single icon system centralize icons?**

| Use Case | Centralizable? |
|---|---|
| Sidebar tool icons | **Partially.** Could use JS to inject SVGs, but this adds complexity. Inline SVGs are simple. |
| Icon rail | **Partially.** Same as above. |
| Provider logos (in JS) | **Already centralized.** All in `static/js/providers.js`. |

**Verdict:** Not worth centralizing. Inline SVGs are part of the HTML structure and changing them is straightforward. The provider logo catalog is already centralized.

### 4.5 Candidate for Centralization: Fonts

**Current state:** `@font-face` declarations in 3 locations (`style.css`, `index.html`, `login.html`). Font map in `theme.js`.

**Can fonts be centralized?**

| Location | Centralizable? |
|---|---|
| `style.css` primary declarations | **No.** CSS `@font-face` must be in CSS. |
| `index.html` Inter declarations | **Yes.** Move Inter `@font-face` to `style.css` alongside Fira Code. |
| `login.html` Fira Code declarations | **Yes.** Remove from login.html — already in `style.css`. |
| `theme.js` font map | **No.** JS needs the map for the font picker. |

**Verdict:** Move Inter `@font-face` from `index.html` to `style.css`. Remove redundant `@font-face` from `login.html` and the duplicate block at `style.css:7954-7956`. These are cleanup items, not branding centralization.

### 4.6 Candidate for Centralization: Favicon

**Current state:** Inline data URI SVG in 3 HTML files + dynamic version in `theme.js` + `static/icon.ico`.

**Can favicons be centralized?**

| Implementation | Centralizable? |
|---|---|
| Static fallback favicon | **Partially.** Could reference a constant from `theme.js` in the inline `<head>` script. |
| Dynamic per-route favicon | **Already centralized.** In `theme.js`. |
| `static/icon.ico` | **No.** Must be a physical file for PyInstaller. |

**Verdict:** The dynamic favicon is already centralized in `theme.js`. The static fallback could theoretically reference the same constant, but the inline `<head>` script runs synchronously before module imports, so it must be self-contained.

### 4.7 Candidate for Centralization: Loading Screens

**Current state:** App loader in `index.html` inline, Python splash in `launcher.py`.

**Can loading screens be centralized?**

| Screen | Centralizable? |
|---|---|
| App loader wave | **Partially.** Color uses `var(--brand-color)`. Text is ASCII-only (no brand text). |
| Python splash | **No.** tkinter widget. Must be modified independently. |

**Verdict:** The app loader already uses CSS variables for color. No additional centralization needed. Python splash must remain separate.

### 4.8 Candidate for Centralization: Application Metadata

**Current state:** `manifest.json` is static. Meta tags in `index.html`.

**Can metadata be centralized?**

| Item | Centralizable? |
|---|---|
| `manifest.json` name/description | **Partially.** Would need server-side templating or a JS-generated Blob URL (already done partially for per-route manifests). |
| `<meta name="theme-color">` | **Already centralized.** Updated by `theme.js` at runtime. |
| `<title>` | **Partially.** Per-route titles set by JS, but initial static `<title>` must exist. |

**Verdict:** The per-route PWA manifest already uses a JS Blob URL pattern that could be extended to centralize all manifest values.

---

## 5. Centralized Branding Layer — Proposed Design

The strongest existing extension point is the **CSS variable system** combined with the **theme.js theme definitions**. A centralized branding layer should extend these, not replace them.

### Layer Structure

```
static/
  maven-hq-branding.js        ← NEW: Single JS module for Maven HQ brand config
  manifest.json               ← MODIFY: Update name, description, icons
  index.html                  ← MODIFY: reference branding.js, update static text
  login.html                  ← MODIFY: reference branding.js, update static text
```

### `maven-hq-branding.js` (proposed)

```javascript
// Centralized Maven HQ brand configuration
// All branding changes should be made here, not scattered across files.

export const BRAND = {
  name: 'Maven HQ',
  shortName: 'Maven HQ',
  tagline: 'Your AI Operating System',
  description: 'A unified workspace for AI applications and business tools',

  // Logo SVG — single source of truth for all frontend logo instances
  logoSvg: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <path d="..." fill="currentColor"/>
  </svg>`,

  // Brand color palette
  colors: {
    accent: '#e06c75',        // --brand-color default (overridable by theme)
    accentGradient: '#9cdef2', // --brand-mix-to default
    bg: '#282c34',
    fg: '#9cdef2',
    panel: '#111111',
    border: '#355a66',
  },

  // Route titles
  titles: {
    '/': 'Maven HQ',
    '/calendar': 'Calendar — Maven HQ',
    '/notes': 'Notes — Maven HQ',
    '/cookbook': 'Cookbook — Maven HQ',
    '/email': 'Email — Maven HQ',
    '/memory': 'Memory — Maven HQ',
    '/gallery': 'Gallery — Maven HQ',
    '/tasks': 'Tasks — Maven HQ',
    '/library': 'Library — Maven HQ',
    '/login': 'Maven HQ — Login',
  },
};
```

### How the Layer Connects

| Surface | Centralized At | How It Reads |
|---|---|---|
| Sidebar brand text | `static/index.html:709` | `BRAND.name` set via JS on DOMContentLoaded. Static fallback stays. |
| Welcome screen | `static/index.html:960` | Same pattern. |
| Browser `<title>` | `static/index.html:5`, 158–167 | JS sets `document.title` from `BRAND.titles[path]`. Static fallback stays. |
| Login `<title>` | `static/login.html:6` | Inline script sets `document.title = BRAND.titles['/login']`. |
| Logo (all frontend) | `BRAND.logoSvg` constant | Injected into welcome screen, login page, favicon via JS at init. |
| Favicon SVG | `BRAND.logoSvg` | Replaces hardcoded SVG data URIs. Color substitution still handled by theme. |
| Brand color | `theme.js` colors | `--brand-color` defaults to `BRAND.colors.accent`. Overridable by theme. |
| PWA manifest | JS-generated Blob URL | Extend existing per-route manifest pattern to read `BRAND.name`, `BRAND.description`. |
| Settings label | `theme.js` `ADV_KEYS` | Label string: `'Maven HQ Logo'`. Already a JS constant. |

---

## 6. File Modification Strategy

### 6.1 Files to Create

| File | Purpose | Classification |
|---|---|---|
| `static/js/maven-hq-branding.js` | Centralized brand config (name, logo SVG, titles, color defaults) | **Recommended** |

### 6.2 Files to Modify (Minimal — Brand Text & Assets Only)

| File | Change | Classification |
|---|---|---|
| `static/index.html` | Static `<title>`, route titles object, sidebar brand text, welcome text, chat meta text, settings labels, AIO heading, favicon data URI, logo SVG in welcome screen | **Required** |
| `static/login.html` | `<title>`, logo SVG + brand text, favicon data URI | **Required** |
| `static/manifest.json` | `name`, `short_name`, `description`, `background_color`, `theme_color` | **Required** |
| `static/sw.js` | Cache name string | **Required** |
| `static/js/theme.js` | `ADV_KEYS` brand label (`'Odysseus Logo'` → `'Maven HQ Logo'`), favicon fallback SVG shape | **Required** |
| `launcher.py` | Splash text, window title, tray name, tray icon drawing | **Required** |
| `Odysseus.spec` | EXE name | **Required** |
| `docs/index.html` | Title, favicon, logo SVGs, brand text | **Required** |

### 6.3 Files to Modify (Recommended — Backend Identity)

| File | Change | Notes |
|---|---|---|
| `routes/auth_routes.py` | Session cookie name, connectivity test messages | Breaks existing sessions. Plan migration. |
| `core/auth.py` | TOTP issuer name | Visible only in authenticator apps. |
| `routes/backup_routes.py` | Backup filename prefix | Affects file listing. |
| `core/middleware.py` | Internal header names | Must coordinate with internal tooling. |
| `app.py` | Env var names (`ODYSSEUS_*`) | Must coordinate with deployed configs. |
| `routes/email_routes.py` | Header names (`X-Odysseus-*`) | Visible in email headers. |
| `static/icon.ico` | Replace with Maven HQ `.ico` | **Required** for PyInstaller build. |

### 6.4 Files to Leave Unchanged

| File | Rationale |
|---|---|
| `static/style.css` (component styles) | Override via CSS variables. Do not edit upstream component CSS. |
| `static/app.js` | Application logic. No branding content. |
| `static/js/` (all modules except theme.js) | No branding content. |
| `routes/*.py` (except auth, backup, email) | API endpoints. No branding. |
| `core/database.py`, `core/constants.py` | Data layer. No branding. |
| `src/` | Backend logic. No branding. |
| `companion/` | Internal bridge. |
| `static/js/providers.js` | Third-party provider logos. |
| `static/icons/ollama-*.png`, `sglang-*.png` | Third-party provider logos. |

---

## 7. Merge Conflict Risk Assessment

| Change | Risk Level | Mitigation |
|---|---|---|
| `static/index.html` brand text | **High** — upstream frequently edits this file | Keep Maven HQ changes in a single contiguous block with comments `<!-- MAVEN HQ BRANDING -->` |
| `static/login.html` | **Medium** — less frequently edited | Same approach |
| `static/js/theme.js` | **Medium** — theme system is stable but large | Isolate Maven HQ changes to specific constants (`ADV_KEYS`, favicon fallback shape) |
| `static/style.css` `:root` variables | **Low** — these are near the top of the file and stable | Change only the `:root` variable values; leave all component styles untouched |
| `launcher.py` | **Low** — small file, infrequently changed | Replace entire splash/tray section |
| `routes/auth_routes.py` cookie name | **Low** — single line, unlikely to change upstream | Change the `SESSION_COOKIE` constant |
| `app.py` env vars | **Low** — stable configuration | Rename with sed-like find-replace |
| `docs/index.html` | **Medium** — may be restructured upstream | Replace entire branding section at end of file |

---

## 8. Recommended Branding Architecture for Maven HQ

### Long-Term Approach

Create a **branding boundary layer** that isolates all Maven HQ identity from the upstream codebase. This layer has three components:

### Layer 1: CSS Variable Override (Lowest Friction)

**Do not modify `style.css` component styles.** Instead, set brand-specific CSS variables at a higher priority than `:root`.

```css
/* static/maven-hq-brand.css — loaded after style.css */
:root {
  --red: #<MAVEN_HQ_ACCENT>;
  --brand-color: #<MAVEN_HQ_ACCENT>;
  --bg: #<MAVEN_HQ_BG>;
  --fg: #<MAVEN_HQ_FG>;
  --panel: #<MAVEN_HQ_PANEL>;
  --border: #<MAVEN_HQ_BORDER>;
  --font-family: '<Brand Font>', 'Fira Code', monospace;
}
```

**Add a single `<link>` to `index.html` and `login.html`** after the main stylesheet. This overrides all upstream CSS variables without touching `style.css`.

**Effect:** The entire application re-colors to Maven HQ's palette. All 39,571 lines of upstream component CSS work unchanged. Zero merge conflict risk for `style.css`.

### Layer 2: Brand Config Module

Create `static/js/maven-hq-branding.js` (described in §5 above). This module exports:

- Brand name, short name, tagline
- Logo SVG markup
- Route titles
- Default color palette
- Favicon SVG template

The existing `index.html` inline `<head>` script reads from this module (or a synchronous inline copy) instead of hardcoding "Odysseus" and the sailboat SVG.

**Effect:** All frontend brand text is controlled from one file. Changing "Odysseus" to "Maven HQ" or the sailboat to a new logo requires editing exactly one JS constant.

### Layer 3: Backend Config Module

Create a Python module for backend branding constants:

```python
# src/maven_hq_branding.py
BRAND = {
    "name": "Maven HQ",
    "session_cookie": "maven_hq_session",
    "totp_issuer": "Maven HQ",
    "backup_prefix": "maven_hq_backup",
    "internal_header_prefix": "X-Maven-HQ-",
    "env_prefix": "MAVEN_HQ_",
    "cache_name": "maven-hq-v1",
}
```

Import this module in `app.py`, `core/auth.py`, `core/middleware.py`, `routes/auth_routes.py`, `routes/backup_routes.py`, `routes/email_routes.py`, `static/sw.js` (via env var injection), and `launcher.py`.

**Effect:** All backend brand strings are controlled from one Python file.

### What This Architecture Achieves

| Goal | How |
|---|---|
| Future branding changes from one location | Edit `maven-hq-branding.js` + `maven-hq-brand.css` + `maven_hq_branding.py` |
| Zero merge conflicts on component CSS | Never touch `style.css` component styles |
| Minimal merge conflicts on HTML | Isolate branding in marked comment blocks |
| Upstream compatibility | CSS variable cascade means upstream component colors update automatically |
| Clean rebranding path | Replace logo assets, update brand config module, done |

---

## 9. Summary Classification

| Change | Classification | Rationale |
|---|---|---|
| Create `static/js/maven-hq-branding.js` | **Recommended** | Centralizes all frontend brand text and logo |
| Create `static/maven-hq-brand.css` | **Recommended** | Overrides upstream CSS variables without editing style.css |
| Create `src/maven_hq_branding.py` | **Recommended** | Centralizes all backend brand strings |
| Update `static/index.html` brand text | **Required** | Browser title, sidebar, welcome screen, settings labels |
| Update `static/login.html` brand text | **Required** | Login title, logo, favicon |
| Update `static/manifest.json` | **Required** | PWA identity |
| Update `static/sw.js` cache name | **Required** | Cache isolation on rebrand |
| Replace icon assets (PNG, ICO, wordmark) | **Required** | Visual identity |
| Update `launcher.py` splash/tray | **Required** | Desktop app identity |
| Update `Odysseus.spec` | **Required** | PyInstaller build |
| Update `static/js/theme.js` labels | **Required** | Settings UI label, favicon fallback |
| Create `/workspace` route and Workspace page | **Required** | Maven HQ landing page |
| Update `routes/auth_routes.py` cookie name | **Recommended** | Clean break from upstream identity |
| Update `core/auth.py` TOTP issuer | **Recommended** | Authenticator app label |
| Update `routes/backup_routes.py` prefix | **Recommended** | Backup file naming |
| Update `core/middleware.py` headers | **Recommended** | Internal protocol identity |
| Update `app.py` env vars | **Recommended** | Environment variable namespace |
| Update `routes/email_routes.py` headers | **Recommended** | Email header identity |
| Update docs images | **Recommended** | Docs site branding |
| Modify `static/style.css` component styles | **Leave As-Is** | Override via brand CSS layer instead |
| Modify `static/js/` modules (except theme.js) | **Leave As-Is** | No branding content |
| Modify `routes/*.py` (except auth/backup/email) | **Leave As-Is** | No branding content |
| Modify `core/database.py`, `core/constants.py` | **Leave As-Is** | No branding content |
| Modify `src/` (except branding module) | **Leave As-Is** | Backend logic |
| Modify `static/js/providers.js` | **Leave As-Is** | Third-party logos, not app branding |
| Modify static/icons/ (Ollama, SGLang logos) | **Leave As-Is** | Third-party provider logos |
| Replace font files (Fira Code, Inter, OpenDyslexic) | **Optional** | Only if changing brand font |
