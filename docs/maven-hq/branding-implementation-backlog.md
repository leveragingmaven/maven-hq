# Maven HQ Branding Sprint — Implementation Backlog

This document outlines the current implementation status of the Maven HQ branding, identifies newly discovered inconsistencies, and provides a structured backlog for the remaining Phase 1 (Branding Foundation) work.

In accordance with the sprint constraints, all tasks related to new features, routing changes, database modifications, authentication changes, or workspace redesigns (including the `/workspace` landing page and launcher integrations from Phases 2–5 of the roadmap) have been excluded. This backlog is strictly focused on branding, visual identity, and naming consistency.

---

## 1. Current Implementation Status

An audit of the repository against the approved design documents reveals that **only the styling foundation has been partially established**:

- **Implemented:**
  - `static/maven-hq-brand.css` was created to override CSS custom properties (`--brand-color`, `--bg`, `--fg`, etc.).
  - `<link rel="stylesheet" href="/static/maven-hq-brand.css">` was added in both `static/index.html` and `static/login.html` inside `<!-- MAVEN HQ BRANDING -->` blocks.
- **Remaining:**
  - All actual string replacements from "Odysseus" to "Maven HQ" in the HTML, JS, and Python files.
  - Creation of the centralized branding layer files (`maven-hq-branding.js` and `maven_hq_branding.py`).
  - Replacing the sailboat SVG logo and PWA/desktop assets.
  - Renaming PyInstaller build specs and system files.

---

## 2. Inconsistencies & Discrepancies Discovered

During the repository analysis, several discrepancies and new branding inconsistencies were identified:

1. **Workspace JS File Name Collision (Critical)**
   - *Issue:* The `roadmap.md` and `workspace-design.md` suggest creating a landing page dashboard module at `static/js/workspace.js`.
   - *Inconsistency:* A file named [workspace.js](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/js/workspace.js) already exists in the repository. It contains critical logic for directory browsing, validating, and scoping agent file/shell tools in chat.
   - *Resolution:* If a workspace landing page is built in a future sprint, the script must be named something else (e.g., `workspace-dashboard.js` or `workspace-page.js`) to avoid completely overwriting and breaking the existing folder scoping capability.
2. **Easter Egg & Utility Command Hardcodings**
   - *Issue:* The `/ascii` command in [slashCommands.js](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/js/slashCommands.js#L5414) defaults to printing "Odysseus" in ASCII art when run without arguments. The hidden `/odysseus` command prints quotes from Homer's *Odyssey* and stamps the chat bubble sender role as "Odysseus".
   - *Resolution:* Update the `/ascii` default value to "Maven HQ" and determine if `/odysseus` should be renamed or removed.
3. **Contact and Theme Download Filenames**
   - *Issue:* Downloading contacts in settings downloads `odysseus-contacts.csv` or `.vcf` (in [settings.js](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/js/settings.js#L4175)). Exporting a custom theme downloads `odysseus_themeName.json` (in [theme.js](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/js/theme.js#L1290)).
   - *Resolution:* Rename the download target prefixes to `maven-hq`.
4. **Missing Notification Icon Assets**
   - *Issue:* The notification system references `/static/favicon.ico` and `/static/favicon.png` which are not present in the workspace.
   - *Resolution:* Create these files with the new Maven HQ icon branding.
5. **Redundant & Scattered Font Declarations**
   - *Issue:* Duplicate `@font-face` declarations exist for Fira Code in `style.css` and `login.html`. Additionally, the `@font-face` blocks for Inter are defined inline in the `<head>` of `index.html` instead of being consolidated in a stylesheet.
   - *Resolution:* Clean up and centralize font declarations in `style.css`.

---

## 3. Branding Implementation Backlog

The following backlog is organized logically by priority and dependencies. It is structured to allow for small, low-risk, sequential commits.

### Item 1: Centralized Branding Layer
* **Description:** Create the centralized branding files to serve as the single source of truth for frontend config and backend constants, avoiding scattered hardcoded replacements.
* **Files Affected:** 
  - `[NEW]` [maven-hq-branding.js](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/js/maven-hq-branding.js)
  - `[NEW]` [maven_hq_branding.py](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/src/maven_hq_branding.py)
* **Priority:** High (Prerequisite for text replacements)
* **Estimated Complexity:** Small
* **Recommended Order:** 1

### Item 2: User-Facing Text Rebranding (App Shell & Login)
* **Description:** Rebrand all visible user-facing text from "Odysseus" to "Maven HQ" in the HTML views, page headers, welcome messages, placeholders, settings, and metadata.
* **Files Affected:**
  - [index.html](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/index.html) (static title, per-route titles script, brand headers, chat placeholder, settings labels)
  - [login.html](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/login.html) (page title, welcome header)
  - [settings.js](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/js/settings.js) (system settings text, help notes)
  - [slashCommands.js](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/js/slashCommands.js) (tour script replies, help headers)
* **Priority:** High
* **Estimated Complexity:** Medium
* **Recommended Order:** 2

### Item 3: Logo SVG and Icon Asset Replacement
* **Description:** Replace the inline sailboat SVG logos with the new Maven HQ SVG logo markup. Overwrite binary icon assets with the new visual branding.
* **Files Affected:**
  - [index.html](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/index.html) (welcome header SVG, favicon SVG)
  - [login.html](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/login.html) (login header SVG, favicon SVG)
  - [theme.js](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/js/theme.js) (dynamic favicon base SVG, `'Odysseus Logo'` label)
  - [icon.ico](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/icon.ico)
  - `static/icons/icon-192.png`, `icon-512.png`, `icon-maskable-512.png`
* **Priority:** High
* **Estimated Complexity:** Medium
* **Recommended Order:** 3

### Item 4: PWA Identity & Service Worker Update
* **Description:** Rebrand the PWA application manifest and bump the Service Worker cache name to isolate the new brand shell.
* **Files Affected:**
  - [manifest.json](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/manifest.json) (manifest title and description)
  - [sw.js](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/sw.js) (update `CACHE_NAME` prefix, comments)
* **Priority:** High
* **Estimated Complexity:** Small
* **Recommended Order:** 4

### Item 5: Desktop App Wrapper Branding (PyInstaller & Launcher)
* **Description:** Update launcher window, splash screen labels, tray icons, and compile settings for building the native executable.
* **Files Affected:**
  - [launcher.py](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/launcher.py) (splash text, window titles, pystray menu strings, PIL tray drawing)
  - `[RENAME]` `Odysseus.spec` &rarr; `MavenHQ.spec` (compile config, target output binary name)
  - [build-windows-portable.ps1](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/build-windows-portable.ps1) (updated spec parameters)
  - [build-macos-app.sh](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/build-macos-app.sh) (App titles, bundle identifiers)
* **Priority:** Medium
* **Estimated Complexity:** Medium
* **Recommended Order:** 5

### Item 6: Backend Environment and Protocol Rebranding
* **Description:** Rename database/session cookies, environment variable namespaces, TOTP issuers, backup file names, and internal API header markers.
* **Files Affected:**
  - [app.py](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/app.py) (rename env vars `ODYSSEUS_*` &rarr; `MAVEN_HQ_*`, headers)
  - [auth.py](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/core/auth.py) (TOTP issuer name)
  - [middleware.py](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/core/middleware.py) (headers `X-Odysseus-Internal-Token` &rarr; `X-Maven-HQ-Internal-Token`)
  - [auth_routes.py](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/routes/auth_routes.py) (session cookie name `odysseus_session` &rarr; `maven_hq_session`)
  - [backup_routes.py](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/routes/backup_routes.py) (prefix name `odysseus_backup`)
  - [email_routes.py](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/routes/email_routes.py) (outgoing headers `X-Odysseus-*`)
  - [setup.py](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/setup.py) (first-time setup text and env variables)
* **Priority:** Medium (Breaks existing active sessions and requires user re-auth; execute during scheduled maintenance)
* **Estimated Complexity:** Medium
* **Recommended Order:** 6

### Item 7: Systemd Service Branding
* **Description:** Rebrand the native system daemon files and system install instructions.
* **Files Affected:**
  - `[RENAME]` `odysseus-ui.service` &rarr; `maven-hq-ui.service` (description and paths)
  - [install-service.sh](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/install-service.sh) (systemd enablement script commands)
* **Priority:** Low
* **Estimated Complexity:** Small
* **Recommended Order:** 7

### Item 8: Easter Eggs, Commands, and Utility Cleanup
* **Description:** Fix internal hardcodings in commands and exported file names.
* **Files Affected:**
  - [slashCommands.js](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/js/slashCommands.js) (update `/ascii` default value, review `/odysseus` quote command)
  - [settings.js](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/js/settings.js) (contacts CSV/VCF download filenames)
  - [theme.js](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/js/theme.js) (custom theme JSON download filename)
* **Priority:** Low
* **Estimated Complexity:** Small
* **Recommended Order:** 8

### Item 9: Typography Consolidation & Asset Cleanup
* **Description:** Clean up redundant `@font-face` blocks and move inline font definitions to the main stylesheet. Create missing favicon file fallbacks.
* **Files Affected:**
  - [style.css](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/style.css) (remove duplicate `@font-face` Fira Code block at lines 7954-7956, add Inter font declarations)
  - [index.html](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/index.html) (remove inline Inter styles)
  - [login.html](file:///C:/Users/Martha%20Newell/Downloads/AI-Apps/maven-hq/static/login.html) (remove duplicate Fira Code styles)
  - `[NEW]` `static/favicon.ico`, `static/favicon.png` (create missing notification assets)
* **Priority:** Low
* **Estimated Complexity:** Small
* **Recommended Order:** 9

### Item 10: Documentation Site Rebranding
* **Description:** Rebrand the documentation site templates, setup guides, and update screenshots.
* **Files Affected:**
  - `docs/index.html` (rebrand title, SVG logos, help text)
  - `docs/setup.md`
  - `docs/odysseus-wordmark.png`, `odysseus.jpg`, `odysseus-browser.jpg` (re-capture screenshots under Maven HQ name and replace wordmark asset)
* **Priority:** Low
* **Estimated Complexity:** Small
* **Recommended Order:** 10
