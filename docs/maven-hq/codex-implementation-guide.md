# Maven HQ — Codex Implementation Guide

**Purpose:** Single reference for an AI coding agent to implement the Maven HQ rebranding, workspace landing page, and external application integration — without requiring extensive repository exploration.

---

## 1. Project Overview

### What Maven HQ Is

Maven HQ is a rebranded AI operating system (forked from Odysseus) that provides a unified workspace for AI applications and business tools. It is a web-based single-page application with a FastAPI Python backend.

### Overall Architecture

```
FastAPI Backend (src/, routes/, core/)
  └── serves static SPA (no build step)
       └── static/index.html  ← app shell
            ├── static/style.css        (39,571 lines, monolithic)
            ├── static/js/*.js          (ES modules, no bundler)
            └── static/login.html       (separate auth page)
```

- **Frontend:** Raw HTML + ES modules (no bundler, no framework). Communication via `CustomEvent` DOM events. CSS variables for theming.
- **Backend:** FastAPI (Python). Routes in `routes/`. Core logic in `core/`. Auth middleware validates `odysseus_session` cookie.
- **Desktop wrapper:** `launcher.py` (tkinter + PyInstaller spec `Odysseus.spec`).
- **No build step.** All changes are direct file edits.

### Primary Design Goals

1. Rebrand all "Odysseus" references to "Maven HQ" without modifying application logic.
2. Create a `/workspace` landing page that serves as the user's home base after login.
3. Integrate external applications (MavenSync, Hermes, n8n, GoHighLevel) as launcher entries, then progressively add connected features.
4. Preserve the existing Odysseus architecture — layer Maven HQ branding on top, never rewrite.

### Guiding Principles

- **Preserve architecture.** All existing Odysseus code stays intact. Maven HQ adds layers on top.
- **Minimize merge conflicts.** Isolate Maven HQ changes in clearly marked blocks. Use CSS variable overrides instead of editing component styles.
- **Prefer extension over modification.** Add new modules, registers, and config objects rather than rewriting existing ones.
- **Reuse existing patterns.** Follow the module pattern used by `notes.js`, `calendar.js`, etc. Follow the route pattern used by `/notes`, `/email`, etc.
- **No duplicate systems.** One app registry. One notification bus. One search extension API. One brand config module.
- **Backward compatibility.** Users who bookmark `/` still see Chat. The Workspace is additive, not destructive.

---

## 2. Current Architecture

### 2.1 Branding

| Attribute | Current Value | Locations |
|---|---|---|
| App name | "Odysseus" | ~30 locations across HTML, JS, Python, config |
| Logo | Sailboat SVG (inline data URIs + inline markup) | `index.html`, `login.html`, `docs/index.html`, `theme.js`, `launcher.py` (Pillow) |
| Favicon | Sailboat SVG data URI + `static/icon.ico` | 3 HTML files, `theme.js`, `static/icon.ico` |
| Fonts | Fira Code (mono), Inter (sans), OpenDyslexic (accessibility) | `style.css`, `index.html`, `login.html` |
| Icons | 100% inline SVGs, `stroke="currentColor"`, no icon libraries | Throughout HTML |
| Color system | 5 base colors (`--bg`, `--fg`, `--panel`, `--border`, `--red`) per theme; ~108 CSS variables | `theme.js` (19 themes), `style.css` (:root defaults) |
| Theme switching | No formal provider. Flat module (`theme.js`) sets CSS vars on `document.documentElement`. | `static/js/theme.js` (~2115 lines) |
| Theme persistence | `localStorage` + server sync via `PUT /api/prefs/theme` | `theme.js`, `routes/prefs_routes.py` |

### 2.2 Routing

- **Server:** FastAPI registers each SPA path individually in `app.py:862-921`. No catch-all wildcard.
- **Client:** `_routeOpen` map in `app.js:1105` dispatches pathname to module openers. Deferred via `window._odysseusRouteOpener`.
- **Current routes:** `/`, `/notes`, `/calendar`, `/cookbook`, `/email`, `/memory`, `/gallery`, `/tasks`, `/library`, `/login` (separate HTML).
- **Default behavior for `/`:** No opener fires. Welcome screen shows. `loadSessions()` auto-selects last session or creates default chat.

### 2.3 Workspace (Current State)

There is **no workspace page today.** The closest concept is the chat welcome screen (`#welcome-screen`), which is scoped inside `#chat-container` and toggled by `chatRenderer.js`.

### 2.4 Theme System

| Layer | Source | What It Controls |
|---|---|---|
| `:root` defaults | `style.css:18-69` | Dark mode base colors |
| `:root.light` | `style.css:71-91` | Light mode overrides (~20 vars) |
| Runtime JS-set | `theme.js` | Accent, brand color, sidebar bg, etc. |
| Layout JS-set | `sidebar-layout.js`, `tileManager.js` | Sidebar width, rail width, dock widths |
| Scoped | Inline | Component-specific vars (`--cat-hue`, `--swatch-color`) |

### 2.5 Integration Strategy (External Apps)

**Three progressive levels:**

| Level | Name | What It Provides | When |
|---|---|---|---|
| L1 | Launcher | Workspace card + sidebar entry + new-tab launch | Phase 3 |
| L2 | Connected | API polling for status, notifications, quick actions | Phase 4 |
| L3 | Embedded | iframe / docked panel — only after technical validation | Phase 5 |

**Applications to integrate:**
- **MavenSync** — External sync/collaboration service (own codebase, own auth). Priority: High.
- **Hermes** — External messaging hub (own codebase, own auth). Priority: High.
- **OmniRoute** — AI request routing gateway (infrastructure, not user-facing). Priority: High.
- **n8n** — Workflow automation (third-party, self-hosted). Priority: Medium.
- **GoHighLevel** — CRM/marketing SaaS. Priority: Medium.

**Key rule:** Start every integration at L1. Only invest in L2 where the external app exposes a useful API. Only attempt L3 after technical validation confirms embedding is possible.

### 2.6 Approved Decisions (Do Not Revisit)

These decisions are finalized. Implement as specified — do not propose alternatives.

1. **Preserve Odysseus architecture.** All existing code stays. Maven HQ layers on top.
2. **Three-layer branding boundary.** CSS override (`maven-hq-brand.css`) + JS brand config (`maven-hq-branding.js`) + Python brand config (`maven_hq_branding.py`). All branding changes flow through these three files.
3. **Do not modify `style.css` component styles.** Only change `:root` variable values. Use the brand CSS layer to override.
4. **Workspace at `/workspace`.** Top-level SPA route. Not a replacement for the welcome screen.
5. **Login redirect goes to `/workspace`.** Controlled by user preference "Default landing page: Chat / Workspace".
6. **Launcher-first integration.** All external apps start at L1. No L2 or L3 implementation before the previous level is validated.
7. **Dynamic app registry.** `registerApp()` in `workspace.js`. Replaces hardcoded `_routeOpen`, `_railToolMap`, `UI_VIS_MAP` entries for external apps.
8. **API keys stay server-side.** The frontend proxies all external API calls through Maven HQ backend (`routes/proxy_routes.py`).
9. **Notification bus uses CustomEvent.** `odysseus:app-notification` event name is grandfathered (not renamed to `maven-hq:`).
10. **Isolate Maven HQ changes in marked comment blocks.** `<!-- MAVEN HQ BRANDING -->` / `<!-- END MAVEN HQ BRANDING -->` in HTML. `// MAVEN HQ BRANDING` in JS. `# MAVEN HQ BRANDING` in Python.

---

## 3. Phase-by-Phase Build Instructions

### Phase 1 — Branding Foundation

**Goal:** Replace all "Odysseus" references with "Maven HQ". Establish the three-layer branding system.

#### Files Expected to Change

| Action | File | What to Do |
|---|---|---|
| **NEW** | `static/maven-hq-brand.css` | CSS variable overrides: `--red`, `--brand-color`, `--bg`, `--fg`, `--panel`, `--border`, `--font-family`. Loaded after `style.css`. |
| **NEW** | `static/js/maven-hq-branding.js` | Export `BRAND` object: `name`, `shortName`, `tagline`, `description`, `logoSvg`, `colors`, `titles` map. |
| **NEW** | `src/maven_hq_branding.py` | Python `BRAND` dict: `name`, `session_cookie`, `totp_issuer`, `backup_prefix`, `internal_header_prefix`, `env_prefix`, `cache_name`. |
| **EDIT** | `static/index.html` | Replace `<title>`, route titles array, sidebar brand text, welcome text, AIO heading, chat meta text, settings labels, favicon SVG data URI, welcome screen logo SVG. Add `<link>` to `maven-hq-brand.css`. |
| **EDIT** | `static/login.html` | Replace `<title>`, logo SVG, brand text, favicon SVG data URI. Add `<link>` to `maven-hq-brand.css`. |
| **EDIT** | `static/manifest.json` | Update `name`, `short_name`, `description`, `background_color`, `theme_color`. |
| **EDIT** | `static/sw.js` | Change cache name from `odysseus-v1` to `maven-hq-v1`. Update banner comment. |
| **EDIT** | `static/js/theme.js` | Change `ADV_KEYS` brand label from `'Odysseus Logo'` to `'Maven HQ Logo'`. Replace favicon fallback SVG shape. |
| **EDIT** | `launcher.py` | Replace splash text ("⛵ Odysseus" → "Maven HQ"), window title, tray name/tooltip, tray icon Pillow drawing (sailboat polygons → Maven HQ logo). |
| **EDIT** | `Odysseus.spec` | Rename EXE name and .spec reference to `MavenHQ`. |
| **EDIT** | `docs/index.html` | Replace `<title>`, favicon SVGs, logo SVGs, brand text. |
| **EDIT** | `routes/auth_routes.py` | Change session cookie name from `odysseus_session` to `maven_hq_session`. |
| **EDIT** | `core/auth.py` | Change TOTP issuer name from `Odysseus` to `Maven HQ`. |
| **EDIT** | `routes/backup_routes.py` | Change backup filename prefix from `odysseus_backup` to `maven_hq_backup`. |
| **EDIT** | `core/middleware.py` | Rename internal headers from `X-Odysseus-*` to `X-Maven-HQ-*`. |
| **EDIT** | `app.py` | Rename env vars from `ODYSSEUS_*` to `MAVEN_HQ_*`. Rename internal headers. Import `maven_hq_branding`. |
| **EDIT** | `routes/email_routes.py` | Rename headers from `X-Odysseus-*` to `X-Maven-HQ-*`. |
| **REPLACE** | `static/icon.ico` | Replace with Maven HQ icon. |
| **REPLACE** | `static/icons/icon-192.png` | Replace with Maven HQ 192×192 PNG. |
| **REPLACE** | `static/icons/icon-512.png` | Replace with Maven HQ 512×512 PNG. |
| **REPLACE** | `static/icons/icon-maskable-512.png` | Replace with Maven HQ maskable 512×512 PNG. |
| **REPLACE** | `docs/odysseus-wordmark.png` | Replace with Maven HQ wordmark. |
| **REPLACE** | `docs/odysseus.jpg` | Replace with Maven HQ screenshot. |
| **REPLACE** | `docs/odysseus-browser.jpg` | Replace with Maven HQ browser shot. |

#### Files That Must NOT Change

| File | Reason |
|---|---|
| `static/style.css` component styles (lines 92+) | Override via CSS variables. Editing component styles creates merge conflicts. |
| `static/js/` modules except `theme.js` | Core application logic. No branding content. |
| `static/app.js` | Event wiring and initialization. No branding content. |
| `routes/*.py` except auth, backup, email | API endpoints. No branding. |
| `core/database.py`, `core/constants.py` | Data layer. No branding. |
| `src/` except branding module | Backend logic. No branding. |
| `companion/` | Internal bridge. |
| `static/js/providers.js` | Third-party provider logos. Not app branding. |
| `static/icons/ollama-*.png`, `sglang-*.png` | Third-party provider logos. |

#### Success Criteria

- [ ] Browser tab shows "Maven HQ" at every route
- [ ] Login page shows Maven HQ branding, logo, favicon
- [ ] Sidebar brand text reads "Maven HQ"
- [ ] Welcome screen shows Maven HQ logo and name
- [ ] PWA manifest reports "Maven HQ"
- [ ] Service worker cache name is `maven-hq-v1`
- [ ] System tray icon shows Maven HQ logo with "Maven HQ" tooltip
- [ ] PyInstaller builds produce `MavenHQ.exe`
- [ ] TOTP issuer shows "Maven HQ"
- [ ] Backup files named `maven_hq_backup_*`
- [ ] Email headers show `X-Maven-HQ-*`
- [ ] Session cookie is `maven_hq_session` (all users re-authenticate)
- [ ] No remaining "Odysseus" in any user-facing surface
- [ ] CSS override layer loads and colors are correct
- [ ] Changing a color in `maven-hq-brand.css` propagates everywhere

---

### Phase 2 — Workspace Landing Page

**Goal:** Create `/workspace` SPA route with fullscreen landing page as the user's post-login home base.

#### Files Expected to Change

| Action | File | What to Do |
|---|---|---|
| **EDIT** | `app.py` | Add `@app.get("/workspace")` SPA route serving `index.html` (near existing routes at line ~862) |
| **EDIT** | `static/app.js` | Add `'/workspace': () => workspaceModule.open()` to `_routeOpen` map |
| **EDIT** | `static/index.html` inline script (~105-197) | Add `/workspace` favicon/title entry; add sidebar `<div class="list-item" id="tool-workspace-btn">`; add icon-rail button `#rail-workspace`; add workspace-panel HTML (hidden); add visibility toggle to Appearance settings |
| **NEW** | `static/js/workspace.js` | Module with `open()`, `close()`, `isOpen()` functions. Follow pattern of `notes.js`. Collapse sidebar to rail on open. |
| **EDIT** | `static/style.css` | Add workspace-panel CSS (fullscreen fixed overlay, `inset:0`, left margin `--icon-rail-w`, z-index stacking) |
| **EDIT** | `static/login.html` | Change login redirect from `window.location.replace('/')` to `window.location.replace('/workspace')` |
| **EDIT** | `static/js/chatRenderer.js` | Guard `hideWelcomeScreen()`/`showWelcomeScreen()` with `if (workspaceModule.isOpen()) return;` |
| **EDIT** | `static/js/sessions.js` | Set `_skipAutoSelect = true` when `window._odysseusRouteOpener` points to workspace |
| **EDIT** | `routes/workspace_routes.py` | Add API endpoints: recent sessions, pinned tools, system status, favorite apps, recent projects |

#### Implementation Details for `workspace.js`

```javascript
let _isOpen = false;

function open() {
    if (_isOpen) return;
    _isOpen = true;
    window._collapseSidebarToRail?.();
    const panel = document.getElementById('workspace-panel');
    if (panel) panel.classList.remove('hidden');
}

function close() {
    if (!_isOpen) return;
    _isOpen = false;
    document.getElementById('workspace-panel')?.classList.add('hidden');
    window._restoreSidebarIfRouteCollapsed?.();
}

function isOpen() { return _isOpen; }

export const workspaceModule = { open, close, isOpen };
```

#### Workspace Panel HTML Structure (add to `static/index.html`)

```html
<div id="workspace-panel" class="workspace-panel hidden">
  <div class="workspace-header">
    <h1>Workspace</h1>
    <button id="workspace-close-btn" title="Close workspace">✖</button>
  </div>
  <div class="workspace-content">
    <!-- Phase 2: dashboard widgets, recent sessions, pinned tools, system status -->
    <!-- Phase 3: favorites row, recent apps, recent projects, app launcher cards -->
  </div>
</div>
```

#### Sidebar Registration

| Step | Detail |
|---|---|
| Sidebar item | `<div class="list-item" id="tool-workspace-btn" data-ui-key="tool-workspace">Workspace</div>` in a new `#workspace-section` above `#tools-section` |
| Icon rail | `<button class="icon-rail-btn" id="rail-workspace" title="Workspace"><svg>...</svg></button>` |
| Rail-to-tool map | Add `'rail-workspace': 'tool-workspace-btn'` to `_railToolMap` (or merge via `Object.assign`) |
| Click handler | In `initializeEventListeners()`: `document.getElementById('tool-workspace-btn')?.addEventListener('click', () => window.location.href = '/workspace')` |
| Visibility | Add `tool-workspace` entry to `UI_VIS_MAP` and Appearance settings toggles |

#### Files That Must NOT Change

| File | Reason |
|---|---|
| `static/js/*.js` except `workspace.js`, `chatRenderer.js`, `sessions.js` | Other modules do not need workspace awareness |
| `routes/*.py` except `workspace_routes.py` | Only workspace API belongs here |
| `core/` | No backend logic changes needed for the workspace page itself |

#### Success Criteria

- [ ] Navigating to `/workspace` loads the workspace panel and collapses sidebar to rail
- [ ] Workspace close button restores sidebar and returns to previous view
- [ ] Login lands on `/workspace` by default (respects user preference)
- [ ] `/workspace` is bookmarkable and works on direct navigation
- [ ] Workspace panel does not conflict with welcome screen
- [ ] Chat auto-session-select is suppressed when workspace is open
- [ ] Appearance settings include Workspace visibility toggle
- [ ] Workspace API endpoints return correct data

---

### Phase 3 — App Registry & Launcher Integration (L1)

**Goal:** Create dynamic app registry and implement L1 launchers for all 5 external applications.

#### Files Expected to Change

| Action | File | What to Do |
|---|---|---|
| **EDIT** | `static/js/workspace.js` | Add `registerApp(config)` function with `Map` registry. Add `openApp(appId)` function. Add favorites management (right-click sidebar → add to favorites, drag-to-reorder, 8-app limit). Add recents tracking (localStorage, max 10). Add recent projects tracking. |
| **EDIT** | `static/index.html` | Add `#apps-section` sidebar section between workspace and sessions sections. Add app launcher cards to workspace panel. Add favorites/recent/recent-projects HTML rows. |
| **EDIT** | `static/js/section-management.js` | Add collapse/expand support for `#workspace-section` and `#apps-section` |
| **EDIT** | `static/app.js` | Add `#apps-section` and external app entries to `UI_VIS_MAP`. Wire app registry at boot. |
| **EDIT** | `static/js/search-chat.js` | Add static app index to Ctrl+K results (client-side, L1). Show "Applications" group. |
| **NEW** | `static/js/maven-sync.js` | L1 launcher: export `open()` → `window.open(MAVENSYNC_URL)`. Register via `registerApp()`. |
| **NEW** | `static/js/hermes.js` | L1 launcher: export `open()` → `window.open(HERMES_URL)`. Deep-link support for conversation URLs. |
| **NEW** | `static/js/n8n.js` | L1 launcher: export `open()` → `window.open(N8N_URL)`. |
| **NEW** | `static/js/gohighlevel.js` | L1 launcher: export `open()` → `window.open(GHL_URL)`. Deep-link support for contact/opportunity URLs. |
| **EDIT** | `routes/workspace_routes.py` | Add `GET /api/apps` endpoint returning app list. Add favorites and recents endpoints. |
| **EDIT** | `static/index.html` (+ `workspace.js`) | OmniRoute: Add settings tab (`data-settings-tab="routing"`) and chat top-bar status dot (gray at L1). |

#### Dynamic App Registry (add to `workspace.js`)

```javascript
const _apps = new Map();

export function registerApp(config) {
  _apps.set(config.id, config);
  // Wire sidebar click → config.open()
  // Wire icon rail via Object.assign(_railToolMap, ...)
  // Add to UI_VIS_MAP
  // Register keyboard shortcut
  // Register search source
  // Start status polling if configured
}

export function openApp(appId) {
  const app = _apps.get(appId);
  if (app) { app.open(); _trackRecent(appId); }
}
```

#### `registerApp()` Config Shape

```javascript
{
  id: 'maven-sync',
  name: 'MavenSync',
  icon: '<svg>...</svg>',
  open: () => { window.open(url); },
  level: 'launcher',           // 'launcher' | 'connected' | 'embedded'
  sidebarSelector: '#tool-maven-sync-btn',
  railId: 'rail-maven-sync',
  railLabel: 'Sync',
  settingsKey: 'tool-maven-sync',
  keyboardShortcut: 'ctrl+alt+s',
  notifDotSelector: '#sync-notif-dot',
  searchSource: null,          // Set at L2
  statusEndpoint: null,        // Set at L2
}
```

#### L1 Module Template (each app module, ~30 lines)

```javascript
// static/js/maven-sync.js
const APP_URL = '/api/prefs/maven_sync_url';  // resolved at runtime

export function open(path = '') {
  fetch(APP_URL)
    .then(r => r.json())
    .then(url => window.open(url + path, '_blank'))
    .catch(() => window.open('https://sync.mavenhq.local', '_blank'));
}

// Registration called from app.js at boot
export function init() {
  if (window.workspaceModule) {
    window.workspaceModule.registerApp({
      id: 'maven-sync',
      name: 'MavenSync',
      icon: '<svg>...</svg>',   // Inline Maven HQ icon
      open: () => open(),
      level: 'launcher',
      sidebarSelector: '#tool-maven-sync-btn',
      railId: 'rail-maven-sync',
      railLabel: 'Sync',
      settingsKey: 'tool-maven-sync',
    });
  }
}
```

#### Sidebar `#apps-section` Structure (add to `static/index.html`)

```html
<div class="section" id="workspace-section">
  <!-- workspace button with aggregate notification dot -->
  <div class="list-item" id="tool-workspace-btn" data-ui-key="tool-workspace">
    Workspace
    <span class="sidebar-notif-dot" id="workspace-notif-dot" style="display:none"></span>
  </div>
</div>

<!-- BEGIN EXTERNAL APPS -->
<div class="section" id="apps-section" data-ui-key="section-apps">
  <div class="list-item" id="tool-maven-sync-btn" data-ui-key="tool-maven-sync">
    <span class="sidebar-notif-dot" id="sync-notif-dot" style="display:none"></span>
  </div>
  <div class="list-item" id="tool-hermes-btn" data-ui-key="tool-hermes">
    <span class="sidebar-notif-dot" id="hermes-notif-dot" style="display:none"></span>
  </div>
  <div class="list-item" id="tool-n8n-btn" data-ui-key="tool-n8n">
    <span class="sidebar-notif-dot" id="n8n-notif-dot" style="display:none"></span>
  </div>
  <div class="list-item" id="tool-ghl-btn" data-ui-key="tool-ghl">
    <span class="sidebar-notif-dot" id="ghl-notif-dot" style="display:none"></span>
  </div>
</div>
<!-- END EXTERNAL APPS -->
```

#### Files That Must NOT Change

| File | Reason |
|---|---|
| `static/js/*.js` except `workspace.js`, `search-chat.js`, new app modules | Existing modules do not need modification |
| `routes/*.py` except `workspace_routes.py` | Existing API endpoints unchanged |
| `static/style.css` component styles | Override via CSS variables. New styles added at end of file. |

#### Success Criteria

- [ ] All 4 external apps open correct URL in new tab via sidebar, workspace card, and Ctrl+K
- [ ] Sidebar `#apps-section` shows all apps with labels
- [ ] Workspace panel shows favorites row (configurable, max 8)
- [ ] Workspace panel shows recent apps row (up to 10)
- [ ] Workspace panel shows recent projects row
- [ ] Ctrl+K search includes "Applications" group
- [ ] Deep-link patterns work for Hermes and GoHighLevel
- [ ] OmniRoute settings tab appears in Settings modal
- [ ] OmniRoute chat top-bar status dot appears (gray)
- [ ] Favorites persist across reloads (server API)
- [ ] Recents update on each app launch (localStorage)
- [ ] `GET /api/apps` returns correct app list
- [ ] Right-click sidebar tool → "Add to Workspace favorites" works

---

### Phase 4 — Connected Status & Notifications (L2)

**Goal:** Add API-powered status indicators, recent activity previews, quick actions, and centralized notification bus.

#### Files Expected to Change

| Action | File | What to Do |
|---|---|---|
| **EDIT** | `static/js/workspace.js` | Add notification bus (`window.addEventListener('odysseus:app-notification')`), status polling framework (`registerAppStatus()`), aggregate badge update |
| **EDIT** | `static/js/search-chat.js` | Add `registerSearchSource()` API for dynamic search results |
| **EDIT** | `static/js/maven-sync.js` | Add L2: status polling, dot update, recent activity card, "Sync now" quick action |
| **EDIT** | `static/js/hermes.js` | Add L2: unread count polling, badge update, recent messages preview, "Compose" quick action |
| **EDIT** | `static/js/n8n.js` | Add L2: workflow status polling, error badge, active/failed counts, "Retry Failed" quick action |
| **EDIT** | `static/js/gohighlevel.js` | Add L2: pipeline summary polling, lead count badge, pipeline widget, "New Contact"/"View Pipeline" quick actions |
| **EDIT** | `static/js/omniroute.js` | Add L2: health polling, route table in settings, latency display, failure/recovery toasts |
| **NEW** | `routes/proxy_routes.py` | Proxy endpoints for each app: `/api/maven-sync/status`, `/api/hermes/unread`, `/api/n8n/workflow-status`, `/api/ghl/pipeline-summary`. Each reads stored API key from prefs, calls external API, returns result. |
| **NEW** | `routes/routing_routes.py` | OmniRoute health endpoint `GET /api/routing/health` (proxies to OmniRoute). Prefix `/api/routing`. |
| **NEW** | `routes/webhook_routes.py` | Webhook receivers for push notifications from external apps. Validates signature, dispatches `odysseus:app-notification`. |

#### Status Polling Framework (add to `workspace.js`)

```javascript
const _statusPolls = {};

function registerAppStatus(appId, opts) {
  const { endpoint, interval = 30000, onStatus } = opts;
  const poll = async () => {
    try {
      const res = await fetch(endpoint);
      const data = await res.json();
      onStatus(data);
    } catch { onStatus({ connected: false }); }
  };
  poll();
  _statusPolls[appId] = setInterval(poll, interval);
}
```

#### Notification Bus (add to `workspace.js`)

```javascript
const _appNotifications = {};

window.addEventListener('odysseus:app-notification', (e) => {
  const { appId, count, message } = e.detail;
  _appNotifications[appId] = { count, message, timestamp: Date.now() };
  _updateWorkspaceBadge();
  if (message) uiModule.showToast(`[${appId}] ${message}`);
});

function _updateWorkspaceBadge() {
  const total = Object.values(_appNotifications).reduce((s, n) => s + n.count, 0);
  const dot = document.getElementById('workspace-notif-dot');
  if (dot) {
    dot.style.display = total > 0 ? '' : 'none';
    dot.textContent = total > 99 ? '99+' : String(total);
  }
}
```

#### Proxy Route Pattern (`routes/proxy_routes.py`)

```python
@router.get("/api/proxy/{app_id}/{path:path}")
async def proxy_app(request: Request, app_id: str, path: str):
    user = get_current_user(request)
    prefs = load_prefs(user)
    app_config = APPS[app_id]  # url + api_key field names
    url = prefs.get(app_config["url_key"])
    key = decrypt(prefs.get(app_config["key_key"]))
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{url}/api/v1/{path}",
            headers={"Authorization": f"Bearer {key}"},
            params=dict(request.query_params),
        )
        return Response(content=resp.content, status_code=resp.status_code)
```

#### Files That Must NOT Change

| File | Reason |
|---|---|
| `routes/auth_routes.py` | No auth changes needed for L2 |
| `core/auth.py` | No core auth changes |
| `app.py` routing | No route registration changes (proxy routes use their own router) |
| `static/style.css` component styles | Already have status dot and badge CSS classes from existing app patterns |

#### Success Criteria

- [ ] Each app's sidebar entry shows correct status dot/badge, updating every 30s
- [ ] Status dots show "disconnected" state on API failure
- [ ] Workspace cards show relevant preview data
- [ ] Quick action buttons launch correct URLs or trigger correct API calls
- [ ] Notifications from external apps appear as toasts
- [ ] Aggregate badge on Workspace sidebar entry shows correct notification count
- [ ] Ctrl+K search returns dynamic results from registered apps
- [ ] All API keys stored server-side, never exposed to frontend
- [ ] OmniRoute settings panel shows route table and latency
- [ ] Webhook endpoints validate signatures before dispatching notifications

---

### Phase 5 — Refinement & Embedded Validation (L3)

**Goal:** Validate iframe embedding for external apps. Polish performance, accessibility, and error handling.

#### Files Expected to Change

| Action | File | What to Do |
|---|---|---|
| **EDIT** | `static/js/maven-sync.js` | If L3 validation passes: add fullscreen iframe embed with auth token passthrough |
| **EDIT** | `static/js/hermes.js` | If L3 validation passes: add quick-prompt side panel iframe (docked right, notes-panel pattern) |
| **EDIT** | `static/js/n8n.js` | If L3 validation passes: add full iframe modal with proxy auth |
| **EDIT** | `app.py` | Add validated embed origins to CSP `frame-src` in `SecurityHeadersMiddleware` |
| **EDIT** | All app modules | Performance audit: lazy-load on first use, optimize polling, minimize reflows |
| **EDIT** | Workspace panel + app modules | Accessibility audit: keyboard nav, screen reader labels, focus management |
| **EDIT** | All app modules | Error handling: offline mode, graceful degradation, retry logic |
| **NEW/EDIT** | `docs/` | User documentation: workspace usage guide, app integration setup |

#### L3 Technical Validation Checklist (execute before implementing any iframe)

For each candidate app, check:
1. `X-Frame-Options` header (must not be `DENY` or `SAMEORIGIN` unless configurable)
2. `Content-Security-Policy frame-ancestors` directive (must include Maven HQ origin)
3. `SameSite` cookie attribute (must be `None; Secure` for cross-origin iframes)
4. `CORS` headers (must include Maven HQ origin)
5. Auth mechanism (cookie sharing, token in query param, or proxy-based)
6. Mixed content (both apps must match HTTP/HTTPS scheme)

**Expected outcomes:**
- **MavenSync:** Likely embeddable (controlled service). **Medium effort.**
- **Hermes:** Embeddable only if there is a dedicated quick-send URL. **Medium effort.**
- **n8n:** Embeddable with server config changes (`N8N_SECURITY_FRAME_OPTIONS`). **Medium effort.**
- **GoHighLevel:** Almost certainly blocked (`X-Frame-Options: DENY`). **Do not attempt.** Accept L1+L2 as final.

#### Files That Must NOT Change

| File | Reason |
|---|---|
| `static/js/search-chat.js` | No search changes needed for L3 |
| `routes/proxy_routes.py` | Proxy routes unchanged by L3 |
| `core/` | No core changes for embedding |
| Third-party app codebases | Never modify external app code. Only configure. |

#### Success Criteria

- [ ] L3 validation documented for each app (success or failure reason)
- [ ] Embedding implemented only for technically confirmed apps
- [ ] CSP `frame-src` includes only validated origins
- [ ] All app modules lazy-load on first use
- [ ] Keyboard navigation works for all workspace interactions
- [ ] Screen reader labels present on all app cards and sidebar entries
- [ ] Offline mode shows last known status
- [ ] Error states show helpful messages

---

## 4. Development Rules

### 4.1 File Modification Rules

1. **Always mark Maven HQ changes.** Use delimited comment blocks:
   - HTML: `<!-- MAVEN HQ BRANDING -->` / `<!-- END MAVEN HQ BRANDING -->`
   - JS: `// MAVEN HQ BRANDING` / `// END MAVEN HQ BRANDING`
   - Python: `# MAVEN HQ BRANDING` / `# END MAVEN HQ BRANDING`
2. **Never edit `style.css` component styles.** Only change `:root` variables. Use `maven-hq-brand.css` for all brand overrides.
3. **Never modify third-party provider logos** (`static/js/providers.js`, `static/icons/ollama-*.png`).
4. **Never modify `companion/`** — internal bridge, not branding-relevant.
5. **Append new CSS at the end of `style.css`** — do not interleave with existing rules.

### 4.2 Module Pattern Rules

Every new module (`workspace.js`, `maven-sync.js`, etc.) must follow the existing ES module pattern:

```javascript
// Module-level state
let _someState = false;

function publicFunction() { /* ... */ }

export const moduleName = { publicFunction };
```

### 4.3 Merge Conflict Prevention

| Risk | Rule |
|---|---|
| Sidebar HTML | Keep external app entries in one contiguous block with `<!-- BEGIN EXTERNAL APPS -->` / `<!-- END EXTERNAL APPS -->` |
| `UI_VIS_MAP` | Group external entries in `_EXTERNAL_APP_KEYS` object, merge via `Object.assign()` |
| `_railToolMap` | Add external entries via `Object.assign(_railToolMap, externalAppMap)` |
| Keyboard shortcuts | Generate external shortcuts dynamically from registry, keep in separate `externalShortcuts` object |
| Search sources | Each app registers independently via `registerSearchSource()` at boot |

### 4.4 Naming Conventions

- **JS modules:** `static/js/kebab-case.js` (follow existing convention)
- **CSS classes:** `.workspace-panel`, `.workspace-header`, `.fav-app` (hyphenated BEM-like, matching existing pattern)
- **HTML IDs:** `#tool-maven-sync-btn`, `#rail-maven-sync`, `#sync-notif-dot`
- **API endpoints:** `/api/maven-sync/status`, `/api/hermes/unread`, `/api/n8n/workflow-status`
- **Event names:** `odysseus:app-notification` (grandfathered — do not rename)
- **localStorage keys:** `odysseus-recent-apps`, `odysseus-favorites` (grandfathered — do not rename)
- **CSS variables:** Existing variables (`--icon-rail-w`, `--sidebar-notif-dot`) — reuse rather than create new ones

### 4.5 State Management Rules

- **Workspace panel open state:** Module-level `_isOpen` boolean in `workspace.js`
- **App registry:** `Map` in `workspace.js` (`_apps`)
- **Status polls:** `_statusPolls` object in `workspace.js`
- **Notifications:** `_appNotifications` object in `workspace.js`
- **Favorites:** Server-side via `PUT /api/prefs/workspace_favorites`
- **Recents:** `localStorage` key `odysseus-recent-apps` (array of `{ appId, timestamp }`)
- **Recent projects:** Server-side via `PUT /api/prefs/recent_projects`

---

## 5. Repository Map

### Frontend (`static/`)

```
static/
  index.html              ← App shell. All UI structure. ~1800 lines.
  login.html              ← Auth page (separate HTML). ~500 lines.
  style.css               ← Monolithic CSS, 39,571 lines. DO NOT EDIT component styles.
  manifest.json           ← PWA manifest. Static JSON.
  sw.js                   ← Service worker. Cache name must change.
  icon.ico                ← PyInstaller .ico (replace in Phase 1)
  fonts/
    FiraCode-*.woff2      ← Monospace font. Keep.
    Inter-*.woff2         ← Sans font. Keep.
    OpenDyslexic-*.woff2  ← Accessibility font. Keep.
  icons/
    icon-192.png          ← PWA icon 192×192 (replace in Phase 1)
    icon-512.png          ← PWA icon 512×512 (replace in Phase 1)
    icon-maskable-512.png ← PWA maskable icon (replace in Phase 1)
    ollama-mark.png       ← Third-party. DO NOT MODIFY.
    sglang-*.png          ← Third-party. DO NOT MODIFY.
  js/
    app.js                ← Event wiring, initialization, routing, UI_VIS_MAP, _railToolMap.
    theme.js              ← Theme system. 2115 lines. ADV_KEYS, favicon fallback must change.
    workspace.js          ← NEW. Workspace module + app registry + notification bus.
    search-chat.js        ← Ctrl+K search. Extend with app index + registerSearchSource().
    chatRenderer.js       ← Welcome screen visibility. Guard against workspace open.
    sessions.js           ← Session management. _skipAutoSelect for workspace.
    section-management.js ← Section collapse/expand. Add workspace/apps sections.
    sidebar-layout.js     ← Layout variables. Keep.
    providers.js          ← Third-party provider logos. DO NOT MODIFY.
    maven-hq-branding.js  ← NEW. Centralized brand config (name, logo SVG, titles).
    maven-sync.js         ← NEW. MavenSync integration module.
    hermes.js             ← NEW. Hermes integration module.
    n8n.js                ← NEW. n8n integration module.
    gohighlevel.js        ← NEW. GoHighLevel integration module.
    omniroute.js          ← NEW. OmniRoute infrastructure module.
  maven-hq-brand.css      ← NEW. CSS variable overrides for branding.
```

### Backend

```
app.py                    ← FastAPI app. SPA routes, auth middleware, SecurityHeadersMiddleware, env vars.
routes/
  auth_routes.py          ← Login/logout, session cookie name. Cookie must change.
  prefs_routes.py         ← User preferences API. Workspace favorites/landing page prefs.
  workspace_routes.py     ← Workspace API: browse, recent sessions, pinned items, /api/apps.
  proxy_routes.py         ← NEW. External app API proxies.
  webhook_routes.py       ← NEW. Webhook receivers for push notifications.
  routing_routes.py       ← NEW. OmniRoute health/status endpoints.
  email_routes.py         ← Email headers. X-Odysseus-* must change.
  backup_routes.py        ← Backup filename. odysseus_backup must change.
core/
  auth.py                 ← TOTP issuer name. Must change.
  middleware.py           ← Internal headers. X-Odysseus-* must change.
  database.py             ← Data layer. DO NOT MODIFY.
  constants.py            ← Constants. DO NOT MODIFY.
src/
  maven_hq_branding.py    ← NEW. Backend branding constants module.
```

### Desktop

```
launcher.py               ← tkinter splash/tray. Splash text, tray icon must change.
Odysseus.spec             ← PyInstaller spec. EXE name must change.
```

### Documentation

```
docs/
  index.html              ← Docs site. Title, favicon SVGs, logo SVGs, brand text must change.
  odysseus-wordmark.png   ← Replace with Maven HQ wordmark.
  odysseus.jpg            ← Replace with Maven HQ screenshot.
  odysseus-browser.jpg    ← Replace with Maven HQ browser shot.
  maven-hq/
    branding-audit.md     ← (reference) Brand element inventory.
    workspace-design.md   ← (reference) Workspace architecture.
    integration-plan.md   ← (reference) External app integration strategy.
    theme-analysis.md     ← (reference) CSS/theme architecture.
    roadmap.md            ← (reference) Phased implementation roadmap.
    codex-implementation-guide.md  ← THIS FILE.
```

---

## 6. Coding Priorities

| Rank | Task | Phase | Why This Priority |
|---|---|---|---|
| 1 | Create `static/maven-hq-brand.css` | P1 | Quick win. Zero risk. Changes entire app color scheme instantly. |
| 2 | Create `static/js/maven-hq-branding.js` | P1 | Centralizes all frontend brand text. Enables all downstream text changes. |
| 3 | Create `src/maven_hq_branding.py` | P1 | Centralizes all backend brand strings. Enables all downstream Python changes. |
| 4 | Update `static/index.html` brand text | P1 | Browser title, sidebar, welcome screen — most visible brand surfaces. |
| 5 | Replace icon assets (ICO, PNGs, docs images) | P1 | Visual identity. Required for all other branding to make sense. |
| 6 | Update `launcher.py` + `Odysseus.spec` | P1 | Desktop app identity. |
| 7 | Update backend identity files (cookie, TOTP, headers, env vars) | P1 | Complete the rebranding. Must coordinate with deployment. |
| 8 | Create `static/js/workspace.js` + `/workspace` route | P2 | Core workspace infrastructure. Required for all integration phases. |
| 9 | Add workspace panel HTML + CSS | P2 | Visual container for all workspace content. |
| 10 | Change login redirect to `/workspace` | P2 | Makes workspace the user's home base. |
| 11 | Build dynamic app registry in `workspace.js` | P3 | Foundation for all external app integration. |
| 12 | Create L1 modules (maven-sync, hermes, n8n, ghl) | P3 | Launcher cards for all external apps. High visibility, low effort. |
| 13 | Add `#apps-section` sidebar section | P3 | Sidebar navigation for external apps. |
| 14 | Extend Ctrl+K search with static app index | P3 | Quick app launch from keyboard. |
| 15 | Add favorites/recents/recent-projects to Workspace | P3 | Makes workspace useful as a daily hub. |
| 16 | Build notification bus + status polling framework | P4 | Shared infrastructure for all L2 features. |
| 17 | Implement L2 for each app (MavenSync, Hermes, n8n, GHL, OmniRoute) | P4 | Connected status and quick actions. |
| 18 | Build `routes/proxy_routes.py` | P4 | Server-side API key proxy for all L2 apps. |
| 19 | Implement `registerSearchSource()` for dynamic search | P4 | App-specific search results in Ctrl+K. |
| 20 | L3 validation for each app | P5 | Technical feasibility check before committing to iframe work. |
| 21 | L3 implementation for validated apps | P5 | Embedding only where technically safe. |
| 22 | Performance, accessibility, and error handling polish | P5 | Production readiness. |

---

## 7. Validation Checklist

### Per-Phase Verification

After each phase, verify **all** success criteria listed in the phase section above.

### Cross-Cutting Checks (Every Phase)

- [ ] No `console.log` or debug code left in production files
- [ ] Existing functionality not broken (chat, calendar, notes, email, etc.)
- [ ] CSS changes do not break existing layout (check sidebar, modals, chat container)
- [ ] All files pass linting/type checking
- [ ] No "Odysseus" references in changed files (unless grandfathered — see note below)
- [ ] `maven-hq-brand.css` loads after `style.css` in both `index.html` and `login.html`
- [ ] Maven HQ changes are wrapped in comment blocks as specified

### Grandfathered "Odysseus" Strings (DO NOT CHANGE)

These are internal technical references that do not affect user-facing branding:
- `localStorage` keys: `odysseus-theme`, `odysseus-custom-themes`, `odysseus-ui-visibility`, `odysseus-recent-apps`
- Event name: `odysseus:app-notification`, `odysseus:routing-status-change`
- Internal variable: `window._odysseusRouteOpener`
- Function names: `startOdysseusApp()`, `_collapseSidebarToRail()`, `_restoreSidebarIfRouteCollapsed()`

### Pre-Deployment Checks (After All Phases)

- [ ] Full branding audit: no user-facing "Odysseus" text
- [ ] Workspace loads correctly on fresh login, bookmark, and direct navigation
- [ ] All 4 external app launchers open correct URLs
- [ ] Status indicators show correct states for all apps at L2
- [ ] Notifications appear as toasts and update aggregate badge
- [ ] Ctrl+K search shows apps and dynamic results
- [ ] Favorites persist across sessions
- [ ] Login redirect respects user preference (Chat vs Workspace)
- [ ] Session cookie rename communicated to all users
- [ ] Deployment env vars updated (`ODYSSEUS_*` → `MAVEN_HQ_*`)
- [ ] Backup naming convention change communicated
- [ ] Rollback plan documented for each phase

---

## 8. Future Work

These items are intentionally deferred until after the initial launch.

### Integration Extensions
- **P2P/WebRTC voice/video:** Not in scope unless an external app provides it
- **Custom widget system for Workspace:** Drag-and-drop dashboard builder. Requires user research.
- **Multi-user workspace layouts:** Shared/collaborative workspaces with permissions.

### Platform Expansion
- **Native mobile app:** Electron or Tauri bundling. Requires separate project.
- **Desktop app auto-updater:** Integrate with PyInstaller + update server.

### Advanced Features
- **Backend app discovery:** `GET /api/apps` returns dynamic app list from database instead of hardcoded registry. Enables zero-code app addition.
- **App marketplace:** UI for discovering and enabling external apps from a catalog.
- **Unified search index:** Full-text search across all integrated apps (not just current Ctrl+K sources).

### Technical Debt
- **CSS deduplication:** Remove duplicate `@font-face` block at `style.css:7954-7956` and from `login.html:88-89`.
- **Inter font `@font-face` consolidation:** Move from `index.html:201-203` to `style.css`.
- **Routing helper function:** Replace individual `@app.get()` calls with a helper that registers multiple SPA paths.
- **Notification icon files:** Create `static/favicon.ico` and `static/favicon.png` referenced by JS but currently missing.
