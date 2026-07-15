# Workspace Landing Page — Design Document

## 1. Architecture Overview

The Maven HQ frontend is a **static SPA** with no build step — raw HTML served by a FastAPI backend. Each "tool" (Calendar, Notes, Email, etc.) is a section in the sidebar that opens a modal or side-panel overlay. There is **no home/dashboard concept today** — the root URL `/` shows the chat welcome screen by default.

---

## 2. Authentication Redirect Chain

| Step | What Happens | File |
|---|---|---|
| User visits `/login` | `login.html` fetches `GET /api/auth/status`. If already authenticated, immediately redirects to `/`. | `static/login.html:301+` |
| User submits credentials | `POST /api/auth/login` with `{username, password, remember, totp_code}`. | `static/login.html`, `routes/auth_routes.py:136-166` |
| Backend validates | On success, sets `odysseus_session` cookie (httponly, samesite=lax, path=/). Returns `{ok: true, username}`. | `routes/auth_routes.py` |
| Frontend finishLogin() | Fires 3 parallel prefetches (`/api/sessions`, `/api/auth/features`, `/api/auth/settings`), then does `window.location.replace('/')`. | `static/login.html:472-488` |
| App root loads | `GET /` serves `static/index.html` via `serve_html_with_nonce()`. `startOdysseusApp()` fires on DOMContentLoaded. | `app.py:862-872`, `static/app.js:3578` |
| Auth check on API calls | Global fetch monkey-patch: any 401 (excluding `/api/auth/`) redirects to `/login`. | `static/app.js:188-196` |
| Middleware auth enforcement | Checks `odysseus_session` cookie. If invalid and not an exempt path, returns 401 or 302 to `/login`. | `app.py:356-469` |

### Impact for Workspace

The login redirect goes **directly to `/`**. To land users on a Workspace page first, you must either:
- Change the `finishLogin()` redirect target in `login.html` to `/workspace`, **or**
- Have the app root detect "first visit" and redirect to `/workspace` client-side.

---

## 3. Frontend Routing Structure

The routing is **URL path-based** (no hash routing for main navigation).

### Server-registered SPA paths

All serve the same `static/index.html`:

```
GET /
GET /notes
GET /calendar
GET /cookbook
GET /email
GET /memory
GET /gallery
GET /tasks
GET /library
```

Defined in `app.py:862-921`. The path `/login` serves `static/login.html` separately. **There is no catch-all wildcard** — each path is individually registered. A new `/workspace` path must be registered explicitly.

### Client-side route dispatch

On page load, `static/app.js:1105` reads `window.location.pathname` and looks it up in the `_routeOpen` map:

```javascript
const _routeOpen = {
    '/notes':    () => { notesModule.openPanel(); },
    '/calendar': () => calendarModule.openCalendar(),
    '/cookbook': () => document.getElementById('tool-cookbook-btn')?.click(),
    '/email':    () => { _collapseSidebarToRail(); /* open email */ },
    '/memory':   () => document.getElementById('tool-memory-btn')?.click(),
    '/gallery':  () => document.getElementById('tool-gallery-btn')?.click(),
    '/tasks':    () => document.getElementById('tool-tasks-btn')?.click(),
    '/library':  () => sessionModule.openLibrary(),
};
```

The opener is **deferred** — stashed in `window._odysseusRouteOpener` and executed from `sessionModule.loadSessions().finally()` (line 4208). Each route also customizes the favicon SVG and `<title>` via an inline script at `index.html:105-197`.

### Default behavior for `/`

When no path is registered in `_routeOpen` (like `/`), no opener fires. The app stays on the welcome screen, and `loadSessions()` attempts to:
1. Auto-select the last used session
2. Auto-create a default model chat if none exists
3. Fall through to showing the welcome screen

---

## 4. Home Page Component (Current Welcome Screen)

The current "home" is the chat welcome screen (`index.html:959-972`):

```html
<div id="welcome-screen">
  <div class="welcome-name"><svg class="welcome-boat">...</svg>Maven HQ</div>
  <div class="welcome-sub" id="welcome-sub">Welcome, type /setup to get started.</div>
  <div class="welcome-tip" id="welcome-tip"></div>
  <button type="button" class="incognito-btn" id="incognito-btn">...Nobody</button>
</div>
```

Visibility toggled by `chatRenderer.js:1436-1482`:
- `hideWelcomeScreen()` — adds `.hidden` class, removes `welcome-active` from container
- `showWelcomeScreen()` — reverses, clears input, retriggers animation

The welcome screen lives **inside the chat container** (`#chat-container`), making it fundamentally chat-scoped. It is not a standalone page.

---

## 5. Sidebar Component

### Structure

The sidebar is static HTML with sections:

```
<div class="sidebar" id="sidebar">
  <div class="sidebar-header">
    <button class="sidebar-hamburger">☰</button>
    <div class="sidebar-brand">Maven HQ</div>
  </div>
  <div class="sidebar-inner">
    <div id="sidebar-new-chat-btn">+ New Chat</div>
    <div id="sidebar-search-btn">Search</div>
    
    <div class="section" id="sessions-section">  <!-- Chats list -->
    <div class="section" id="email-section">      <!-- Email accounts -->
    <div class="section" id="models-section">      <!-- Model selector -->
    <div class="section" id="tools-section">        <!-- Tool buttons -->
      <div class="list-item" id="tool-calendar-btn">Calendar</div>
      <div class="list-item" id="tool-cookbook-btn">Cookbook</div>
      ...
    </div>
  </div>
  <div class="sidebar-user-bar">...</div>
</div>
```

### Icon rail

A minimized 48px rail (`#icon-rail`) mirrors the most-used tools and is toggled independently of the full sidebar.

### Visibility control

Each sidebar element has a `data-ui-key` attribute. The Appearance settings panel (`index.html:1720-1800`) provides toggles that persist to localStorage under `odysseus-ui-visibility`. The logic is in `app.js:2600-2677` (`UI_VIS_MAP`, `loadUIVis()`, `applyUIVis()`).

### Section management

Sections are collapsible (state persisted in localStorage). Order is reorderable via drag-and-drop.

---

## 6. Best Location for a New Workspace Page

### Recommendation: Top-level SPA route at `/workspace`

The Workspace page should be a **first-class top-level route** that replaces the chat view, following the pattern established by `/notes` and `/email` which go fullscreen.

#### Rationale

| Consideration | Recommendation |
|---|---|
| **Existing pattern** | `/notes` and `/email` collapse the sidebar to the icon rail and go fullscreen. The Workspace should follow this pattern — it takes over the main content area. |
| **No disruption** | A top-level route does not interfere with the chat welcome screen, session loading, or any existing tool. |
| **Server-side registration** | Add a single line in `app.py` to serve `index.html` at `/workspace`. |
| **Client-side routing** | Add a single entry `'/workspace': () => workspaceModule.open()` to `_routeOpen`. |
| **Auth gating** | Already handled by `AuthMiddleware` — `/workspace` is a non-API path, so unauthenticated users will be redirected to `/login` automatically. |
| **Bookmarkable** | Users can bookmark `/workspace` and land there directly. |

### Alternative considered: Replace the welcome screen

Making the welcome screen show Workspace content was rejected because:
- The welcome screen is deeply integrated with chat state (new chat creation, incognito mode, `/setup` flow)
- It appears and disappears based on session selection
- A Workspace is conceptually separate from chat

---

## 7. Navigation Flow

### Recommended flow

```
Login (/login)
    │
    ▼  redirect
Workspace (/workspace)       ← Landing page after auth
    │
    ├── Click "New Chat"  ──→  Chat (/  or #/session-id)
    ├── Click tool icon   ──→  Tool modal (Calendar, Notes, etc.)
    ├── Click "Settings"  ──→  Settings panel
    └── Click "Workspace" ──→  Stay on Workspace
```

### How to implement the redirect

**Option A (recommended): Change login redirect**

In `static/login.html:487`, change:
```javascript
window.location.replace('/');
```
to:
```javascript
window.location.replace('/workspace');
```

**Option B: Client-side redirect on first visit**

In `static/app.js`, during initialization, read a `firstVisit` flag. If set and the user landed on `/` without a specific session target, redirect to `/workspace`.

### Navigation back to Workspace

The sidebar should have a **Workspace** button:
- Add a new `.list-item` to `#tools-section` in the sidebar HTML
- Add a corresponding icon-rail button in `#icon-rail`
- Register the click handler in `initializeEventListeners()` that does `window.location.href = '/workspace'`
- Add a visibility toggle in the Appearance settings panel

---

## 8. Component Implementation Strategy

### Workspace as a module (following existing patterns)

Create `static/js/workspace.js` following the module pattern:

```javascript
// Module-level state
let _isOpen = false;

function open() {
    if (_isOpen) return;
    _isOpen = true;
    // Collapse sidebar to rail (like /notes, /email)
    window._collapseSidebarToRail?.();
    // Show workspace panel
    const panel = document.getElementById('workspace-panel');
    if (!panel) createPanel();
    panel.classList.remove('hidden');
    // Notify other modules to hide
    if (window.chatModule?.hideWelcomeScreen) window.chatModule.hideWelcomeScreen();
}

function close() {
    if (!_isOpen) return;
    _isOpen = false;
    document.getElementById('workspace-panel')?.classList.add('hidden');
    window._restoreSidebarIfRouteCollapsed?.();
}

export const workspaceModule = { open, close };
```

### Registration

| Concern | File | Change |
|---|---|---|
| Server route | `app.py:862` (SPA route list) | Add `@app.get("/workspace")` serving `index.html` |
| Client route | `static/app.js:1165` (`_routeOpen`) | Add `'/workspace': () => workspaceModule.open()` |
| Favicon/title | `static/index.html:105-197` | Add `/workspace` entry with title `'Workspace — Maven HQ'` and SVG icon |
| Sidebar tool | `static/index.html:Tools section` | Add `<div class="list-item" id="tool-workspace-btn">Workspace</div>` |
| Icon rail | `static/index.html:icon-rail` | Add `<button class="icon-rail-btn" id="rail-workspace">...Workspace</button>` |
| Rail-to-tool map | `static/app.js:3654` (or inline `_railToolMap`) | Add `'rail-workspace': 'tool-workspace-btn'` |

### Panel structure

The Workspace panel should be a sibling of the chat container, following the same insertion pattern as notes or compare:

```html
<div id="workspace-panel" class="workspace-panel hidden">
  <div class="workspace-header">
    <h1>Workspace</h1>
    <button id="workspace-close-btn" title="Close workspace">✖</button>
  </div>
  <div class="workspace-content">
    <!-- Dashboard widgets, recent activity, quick actions -->
  </div>
</div>
```

CSS follows the fullscreen panel pattern: `position:fixed; inset:0; z-index:...` with a left margin matching the icon-rail width (`--icon-rail-w`).

---

## 9. Architectural Concerns & Opportunities

### Concerns

| Concern | Details | Mitigation |
|---|---|---|
| **No generic catch-all routing** | The FastAPI server registers each SPA path individually. Forgetting `/workspace` in the server route list causes 404 on hard reload. | Add a comment/checklist in `app.py` near the existing route list. Consider a helper function that takes a list of paths and registers them all. |
| **CSP nonce injection** | `serve_html_with_nonce()` reads `index.html` as a string template. No change needed unless you add inline `<script>` blocks. | Use the existing mechanism; inline scripts in the panel HTML must use `{{CSP_NONCE}}`. |
| **Welcome screen interference** | Starting a new chat auto-hides the welcome screen and shows chat. If the welcome screen logic conflicts with Workspace, guard the calls with `!_workspaceOpen`. | Wrap `hideWelcomeScreen`/`showWelcomeScreen` calls in a check for `workspaceModule.isOpen()`. |
| **Session auto-load** | `loadSessions()` auto-selects the last session or creates a default chat. On `/workspace`, this is wasted work. | The route opener fires inside `loadSessions().finally()` — the session list still loads, but the auto-select can be skipped with `_skipAutoSelect = true` when the workspace route is active. |
| **Service worker cache** | `sw.js` caches the app shell. If `/workspace` route HTML differs, the cache must be updated. | The shell is `index.html` served from the same file — no change needed. |

### Opportunities

| Opportunity | Details |
|---|---|
| **Workspace API** | The existing `routes/workspace_routes.py` provides `/api/workspace/browse` for filesystem browsing. Extend this with new endpoints for workspace metadata, pinned items, recent activity. |
| **Current model endpoint** | `GET /api/default-chat` returns the configured default model. Use this on the Workspace to show the user's active model and allow quick model switching. |
| **Prefetch pipeline** | The login page already prefetches sessions, features, and settings. Add a Workspace-specific prefetch endpoint that bundles workspace metadata (recent sessions, pinned tools, system status). |
| **Sidebar section for Workspace** | Add a dedicated `.section` in the sidebar just for Workspace (above Tools), making it an app-level navigation island rather than just another tool button. |
| **User preferences API** | `routes/prefs_routes.py` provides per-user preferences. Store workspace layout, pinned widgets, or default landing page preference. |
| **Settings toggle for default landing page** | Add a setting "Default page after login: Chat / Workspace" that controls whether the login redirect goes to `/` or `/workspace`. Persist via prefs API. |

---

## 10. Implementation Checklist

| # | Task | File(s) |
|---|---|---|
| 1 | Add `@app.get("/workspace")` to server SPA routes | `app.py` |
| 2 | Register route in `_routeOpen` map | `static/app.js` |
| 3 | Add favicon/title customization for `/workspace` | `static/index.html` inline script |
| 4 | Create `static/js/workspace.js` (open/close/toggle) | New file |
| 5 | Create workspace-panel HTML (hidden by default) | `static/index.html` |
| 6 | Create workspace-panel CSS | `static/style.css` |
| 7 | Add sidebar list-item for Workspace | `static/index.html` sidebar Tools section |
| 8 | Add icon-rail button for Workspace | `static/index.html` icon rail |
| 9 | Wire rail-to-tool mapping | `static/app.js` (or inline) |
| 10 | Register click handler in `initializeEventListeners()` | `static/app.js` |
| 11 | Add visibility toggle in Appearance settings | `static/index.html` Apperance panel |
| 12 | Change login redirect to `/workspace` (or add first-visit check) | `static/login.html` |
| 13 | Guard welcome screen functions against workspace open | `static/js/chatRenderer.js`, `static/js/sessions.js` |
| 14 | Add Workspace API endpoints as needed | `routes/workspace_routes.py` |
| 15 | Test: direct navigation, login redirect, sidebar back-button | All |
