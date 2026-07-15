# External Application Integration Plan

## 1. Architectural Context

Maven HQ is a **static SPA** (no build step, raw ES modules, FastAPI backend). The UI is organized around:

- **Sidebar + icon rail** — navigation for all tools
- **Chat container** — primary content area (chat messages, welcome screen)
- **Modals** — floating, fullscreen, edge-docked, or side-panel overlays
- **Settings modal** — tabbed sidebar + panel layout
- **Minimize dock** — bottom-of-screen chips for minimized modals
- **Toast notification** — singleton with CSS slide animation
- **Custom DOM events** — cross-module communication via `CustomEvent`
- **localStorage + per-user prefs API** — state persistence

There is **no plugin/extension framework**. Adding external applications requires modifying the codebase in predictable locations (see the registration checklist in §11).

---

## 2. Integration Philosophy

MavenSync, Hermes, n8n, and GoHighLevel are **existing independent applications** with their own codebases, deployments, authentication, and interfaces. Maven HQ is a **unified launch point**, not a platform that rebuilds their UIs.

Three progressive integration levels:

| Level | Name | What It Provides |
|---|---|---|
| **L1** | Launcher | Workspace card, sidebar entry, new-tab/deep-link launch. Default first implementation. |
| **L2** | Connected | API-powered status indicators, recent activity, notifications, quick actions. No duplication of the external app interface. |
| **L3** | Embedded | iframe, docked panel, or deeper UI integration — only where technically safe and genuinely valuable. Requires validation of auth, CSP, `X-Frame-Options`, cookies, CORS, and maintenance cost. |

**Rule:** Start every integration at L1. Only invest in L2 where the external app exposes a useful API. Only invest in L3 where embedding is technically confirmed and the UX gain justifies the maintenance burden.

---

## 3. Integration Methods — Decision Matrix

| Method | Best For | Cost |
|---|---|---|
| **New-tab launch** (`window.open` / `<a target="_blank">`) | Any external app — always works, preserves full app context | Zero effort, poorest UX (tab switching) |
| **Deep link** (custom protocol or direct URL) | Apps with known URL patterns for specific records | Low effort, smooth navigation |
| **Launcher card** (Workspace tile + sidebar entry) | All apps at L1 | Low effort, user discovers all tools in one place |
| **API polling** (status, unread count, recent activity) | Apps with accessible APIs at L2 | Medium effort, no UI duplication |
| **Webhook receiver** (push notifications) | Apps that can send webhooks to Maven HQ | Medium effort, real-time updates |
| **iframe embed** (in a modal/fullscreen container) | Third-party web UIs at L3 — only after technical validation | High effort, fragile (CSP, XFO, CORS, auth tokens, mixed content) |
| **Native ES module** | Only for services fully owned and designed to share auth/Middleware | Highest effort, tightest integration |

---

## 4. Recommended Strategy Per Application

### 4.1 MavenSync — Launcher First, Connected Later

**Role:** External sync/collaboration service. Own codebase, own deployment, own auth.

**Approach:** MavenSync is a standalone application. Maven HQ should launch it, not rebuild it.

| Level | Implementation |
|---|---|
| **L1 — Launcher** | Workspace card + sidebar entry + new-tab launch. User clicks → app opens in new tab. Maven HQ maintains its own session. |
| **L2 — Connected** | SSO-based session sharing (same auth provider). API polling for sync status, recent sync activity, conflict count. Status dot in sidebar. Quick action: "Sync now" button on Workspace card triggers the external app's sync API. |
| **L3 — Embedded** | Only if auth, CSP, and UX justify it. Fullscreen iframe or docked panel. Must validate `X-Frame-Options` on MavenSync's side before committing. |

**L1 implementation:**

| Concern | Detail |
|---|---|
| Module file | `static/js/maven-sync.js` — ~30 lines. Exports `open()` which calls `window.open(MAVENSYNC_URL)`. |
| Config | MavenSync URL stored via `PUT /api/prefs/maven_sync_url`. Default from env var `MAVENSYNC_URL`. |
| Sidebar | Add `#tool-maven-sync-btn` to `#apps-section` in sidebar. Click handler calls `open()`. |
| Icon rail | Add `#rail-maven-sync` with label `Sync`. Wire via `_railToolMap`. |
| Workspace card | Tile with icon, name, status dot (gray at L1). Click → `open()`. |
| Route (optional) | `/sync` could redirect to MavenSync URL via server-side 302. |

**L2 additions:**

| Concern | Detail |
|---|---|
| Status API | `GET /api/maven-sync/status` proxy → MavenSync health endpoint. Returns `{ connected, lastSync, conflictCount, recentActivity[] }`. |
| Status dot | `.sidebar-notif-dot` green/gray/red, updated on 30s polling interval. |
| Recent activity | Shown on Workspace card as a small feed. |
| Quick action | "Sync now" button on card calls `POST /api/maven-sync/trigger-sync` proxy. |
| Notification | Webhook from MavenSync → `odysseus:app-notification` event → toast + badge. |

---

### 4.2 Hermes — Launcher First, Optional Quick-Prompt Later

**Role:** External messaging/communication hub. Own codebase, own auth.

**Approach:** Hermes is a full messaging application. Maven HQ does not rebuild the message list or compose UI.

| Level | Implementation |
|---|---|
| **L1 — Launcher** | Workspace card + sidebar entry + new-tab/deep-link launch. Optionally deep-link to a specific conversation or contact. |
| **L2 — Connected** | API polling for unread count and recent messages. Notification badge on sidebar entry. Workspace card shows last message preview. Quick action: "Compose" opens Hermes compose URL. |
| **L3 — Embedded** | Lightweight quick-prompt side panel: an iframe showing a stripped-down Hermes "quick send" view, docked to the right (notes-panel pattern). Only if Hermes provides a dedicated embed URL. |

**L1 implementation:**

| Concern | Detail |
|---|---|
| Module file | `static/js/hermes.js` — launches `window.open(HERMES_URL)` or deep-links to `HERMES_URL/conversation/{id}`. |
| Config | Hermes URL via `PUT /api/prefs/hermes_url`. Default from env var. |
| Sidebar | `#tool-hermes-btn` in `#apps-section`. |
| Workspace card | Tile showing app name, optional login status. |

**L2 additions:**

| Concern | Detail |
|---|---|
| Unread API | `GET /api/hermes/unread` proxy → returns `{ count, latest[] }`. |
| Badge | `#hermes-unread-dot` on sidebar item with count. Pulsing via `email-notif-breathe` CSS animation. |
| Recent messages | Small feed on Workspace card. |
| Quick action | "Compose" button opens `HERMES_URL/compose` in new tab. |
| Deep link | `hermes://conversation/{id}` protocol handler or direct URL construction. |

---

### 4.3 OmniRoute — Infrastructure Integration

**Role:** AI request routing/gateway. Infrastructure, not a user-facing sidebar application.

**Approach:** Invisible during normal operation. Only surfaces as a status indicator and settings panel.

| Level | Implementation |
|---|---|
| **L1 — Launcher** | Not applicable. No user-facing launch needed. |
| **L2 — Connected** | Status dot in chat top-bar. Settings panel with route table, latency, fallback chains. Toast on routing failure. |
| **L3 — Embedded** | Not applicable. No meaningful UI to embed. |

**L2 implementation:**

| Concern | Detail |
|---|---|
| Module file | `static/js/omniroute.js` — lightweight, exports status polling + settings panel wiring. |
| Sidebar | **No sidebar button.** OmniRoute is infrastructure, not a user tool. |
| Settings tab | Add `data-settings-tab="routing"` + `data-settings-panel="routing"` to settings modal. |
| Header indicator | Small `<span>` in `.chat-top-bar` (next to `#current-meta`): green/red dot + "OmniRoute" label. |
| Status polling | `GET /api/routing/health` at 30s interval. |
| Notifications | `odysseus:routing-status-change` event → toast on connection loss/recovery. |
| Backend API | New `routes/routing_routes.py` prefix `/api/routing`. Proxies to OmniRoute health/status endpoints. |

**Settings panel content:**
```html
<div data-settings-panel="routing" class="hidden">
  <h2>OmniRoute</h2>
  <div class="routing-status-bar">
    <span class="routing-dot" id="routing-dot"></span>
    <span id="routing-status-text">Connected</span>
    <span id="routing-latency"></span>
  </div>
  <div class="admin-card">
    <h3>Route Table</h3>
    <div id="routing-route-table"></div>
  </div>
  <div class="admin-card">
    <h3>Fallback Chains</h3>
    <div id="routing-fallbacks"></div>
  </div>
</div>
```

---

### 4.4 n8n — Launcher First, Workflow Status Second, iframe Last

**Role:** Workflow automation (third-party, self-hosted).

**Approach:** n8n is a full web application. Start with a launcher; add API-driven workflow status before considering iframe embedding.

| Level | Implementation |
|---|---|
| **L1 — Launcher** | Workspace card + sidebar entry + new-tab launch. Configurable n8n URL. |
| **L2 — Connected** | Poll n8n REST API for workflow statuses (active/failed/paused). Show execution count and recent failures. Badge on sidebar when workflows have errors. Quick action: "Open Workflows" launches n8n. |
| **L3 — Embedded** | iframe fullscreen modal — **only after technical validation**. n8n must not set `X-Frame-Options: DENY`. Must support embedding cookies or token-based auth. If embedding fails, L1 + L2 are sufficient. |

**Technical validation checklist for L3 iframe:**

| Check | Where | Failure Mitigation |
|---|---|---|
| `X-Frame-Options` header | n8n HTTP response headers | Add `n8n` config option `N8N_SECURITY_FRAME_OPTIONS` or use middleware |
| `Content-Security-Policy frame-ancestors` | n8n HTTP response headers | Add Maven HQ origin to n8n's CSP |
| SameSite cookies | n8n session cookie | Must be `SameSite=None; Secure` for cross-origin iframe |
| CORS headers | n8n API responses | Must include Maven HQ origin in `Access-Control-Allow-Origin` |
| Auth token in query param | n8n supports `?apiKey=` | Fall back to cookie-based auth if not supported |
| Mixed content (HTTP vs HTTPS) | Both apps must match scheme | Upgrade both to HTTPS |

**L1 implementation:**

| Concern | Detail |
|---|---|
| Module file | `static/js/n8n.js` — launches `window.open(N8N_URL)`. |
| Config | n8n URL via `PUT /api/prefs/n8n_url`. |
| Sidebar | `#tool-n8n-btn` in `#apps-section`. |
| Workspace card | Tile showing n8n icon + "Workflows" label. |

**L2 additions:**

| Concern | Detail |
|---|---|
| Workflow status API | Proxy `GET /api/workflows` → n8n REST API `/rest/workflows`. Returns `{ workflows: [{ id, name, active, failed }] }`. |
| Sidebar badge | Red dot when any workflow has errors. |
| Workspace card | Shows active/failed workflow counts. |
| Quick action | "Open Workflows" → new tab. "Retry Failed" → `POST /api/workflows/{id}/retry` proxy. |

---

### 4.5 GoHighLevel — Launcher + Deep Links First, API Summaries Second, iframe Last

**Role:** CRM / marketing platform (third-party SaaS).

**Approach:** GHL is an external SaaS with likely `X-Frame-Options` restrictions. Start with launcher and deep links. Add API summaries at L2. Only attempt iframe at L3 after explicit validation.

| Level | Implementation |
|---|---|
| **L1 — Launcher** | Workspace card + sidebar entry + new-tab launch. Deep-link support: `ghl://contact/{id}`, `ghl://opportunity/{id}` patterns render as clickable links in chat. |
| **L2 — Connected** | Poll GHL API (via Maven HQ proxy) for lead count, opportunity count, recent activity. Sidebar badge for new leads. Workspace card shows pipeline summary. Quick actions: "New Contact", "View Pipeline". |
| **L3 — Embedded** | Full UI iframe — **low priority.** GHL almost certainly sets `X-Frame-Options: DENY`. Even if unset, cookie-based auth across origins is unreliable. A proxy-based approach may partially work but adds significant complexity. |

**L1 implementation:**

| Concern | Detail |
|---|---|
| Module file | `static/js/gohighlevel.js` — launches `window.open(GHL_URL)` with optional path. |
| Config | GHL URL + API key via `PUT /api/prefs/ghl_url`, `PUT /api/prefs/ghl_api_key`. |
| Sidebar | `#tool-ghl-btn` in `#apps-section` with label `CRM`. |
| Workspace card | Tile with GHL icon + "CRM" label. |
| Deep link parsing | `chatRenderer.js` auto-link patterns like `ghl://contact/123` to `GHL_URL/location/{locId}/contact/123`. |

**L2 additions:**

| Concern | Detail |
|---|---|
| Pipeline summary API | Proxy `GET /api/ghl/pipeline-summary` → GHL API. Returns `{ leads, opportunities, tasks }`. |
| Sidebar badge | `#ghl-notif-dot` with count of new leads since last viewed. |
| Workspace card | Shows pipeline summary widget. |
| Quick actions | "New Contact" → `GHL_URL/location/{locId}/contact/new`. "View Pipeline" → `GHL_URL/location/{locId}/pipeline`. |

---

## 5. Authentication Strategy

| Application | L1 (Launcher) | L2 (Connected) | L3 (Embedded) |
|---|---|---|---|
| **MavenSync** | User logs into MavenSync independently in new tab | SSO via shared auth provider (OIDC/SAML). Maven HQ backend proxies API calls with service account token. | Shared session cookie if on same domain/origin; otherwise token-based SSO. |
| **Hermes** | User logs into Hermes independently in new tab | SSO via shared auth provider. Unread count API proxies with service account. | iframe cookie sharing requires `SameSite=None; Secure` + same top-level domain. |
| **OmniRoute** | N/A | Backend-to-backend API key. No user auth needed. | N/A |
| **n8n** | User logs into n8n independently in new tab | n8n API key stored via `PUT /api/prefs/n8n_api_key`. Backend proxies API calls with the key. | n8n cookie in iframe; or pass `apiKey` query param if n8n supports it. |
| **GoHighLevel** | User logs into GHL independently in new tab | GHL API key / OAuth token stored via `PUT /api/prefs/ghl_api_key`. Backend proxies API calls. | Requires GHL to allow embedding and support token-based auth in iframe. Unlikely. |

**Proxy pattern for L2 API calls:**

```python
# routes/proxy_routes.py
@router.get("/api/proxy/n8n/{path:path}")
async def proxy_n8n(request: Request, path: str):
    user = get_current_user(request)
    prefs = load_prefs(user)
    n8n_url = prefs.get("n8n_url")
    n8n_key = decrypt(prefs.get("n8n_api_key"))
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{n8n_url}/api/v1/{path}",
            headers={"Authorization": f"Bearer {n8n_key}"},
            params=dict(request.query_params),
        )
        return Response(content=resp.content, status_code=resp.status_code)
```

This keeps API keys server-side. The frontend never sees them.

---

## 6. Status Indicators

| Application | L1 | L2 |
|---|---|---|
| **MavenSync** | Gray dot (no status) | Green/gray dot on sidebar + Workspace card. Poll `GET /api/maven-sync/status`. |
| **Hermes** | Gray dot | Unread count badge on sidebar. Poll `GET /api/hermes/unread`. |
| **OmniRoute** | Gray dot in top-bar | Green/red dot + latency in top-bar. Poll `GET /api/routing/health`. |
| **n8n** | Gray dot | Red dot on workflow failure. Poll `GET /api/n8n/workflow-status`. |
| **GoHighLevel** | Gray dot | Count badge for new leads. Poll `GET /api/ghl/pipeline-summary`. |

**Generic L2 status polling pattern (in `workspace.js`):**

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

---

## 7. Cross-Application Notifications

**Architecture:** A centralized notification bus using `CustomEvent`.

At L2, each app module can push notifications to Maven HQ:

```javascript
// workspace.js — central notification hub
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

**Notification sources:**
- **MavenSync:** Webhook on sync conflict → `{ appId: 'maven-sync', count: 1, message: 'Sync conflict in Q4 docs' }`
- **Hermes:** Webhook or poll-based unread count → `{ appId: 'hermes', count: 3, message: '3 unread messages' }`
- **n8n:** Webhook on workflow failure → `{ appId: 'n8n', count: 1, message: 'Workflow "Invoice" failed' }`
- **GoHighLevel:** Poll-based new lead count → `{ appId: 'ghl', count: 2, message: '2 new leads' }`
- **OmniRoute:** Internal status change → `{ appId: 'omniroute', count: 0, message: 'Route failover to backup provider' }`

---

## 8. Workspace Landing Page Integration

The Workspace page (`/workspace`) is the aggregator for all integrated applications.

### 8.1 Favorite Applications

**Storage:** `PUT /api/prefs/workspace_favorites` stores an ordered array of app IDs.

**UI:** A row of icon tiles at the top of Workspace:

```html
<div class="workspace-favorites">
  <div class="fav-app" data-app-id="maven-sync">
    <div class="fav-app-icon"><svg>...</svg></div>
    <span class="fav-app-name">Sync</span>
    <span class="fav-app-status" id="status-maven-sync"></span>
  </div>
  <div class="fav-app" data-app-id="hermes">
    <div class="fav-app-icon"><svg>...</svg></div>
    <span class="fav-app-name">Messages</span>
    <span class="fav-app-badge" id="badge-hermes"></span>
  </div>
  ...
</div>
```

**Managing favorites:**
- Right-click any sidebar tool → "Add to Workspace favorites"
- Workspace "Customize" mode: drag-to-reorder, × to remove
- Limit to 8 apps

### 8.2 Recent Applications

**Storage:** `localStorage` key `odysseus-recent-apps` (array of `{ appId, timestamp }`).

**Tracking:** Each `workspaceModule.openApp(appId)` call pushes to the front (max 10 entries).

**UI:** Secondary row below favorites:

```html
<div class="workspace-recent">
  <span class="workspace-section-label">Recent</span>
  <div class="recent-app-list">
    <button class="recent-app" data-app-id="n8n"><svg>...</svg> Workflows</button>
    ...
  </div>
</div>
```

### 8.3 Recently Opened Projects

**Concept:** A "project" is a work context — a chat session, a document, or an external app record (GHL contact, n8n workflow).

**Storage:** `PUT /api/prefs/recent_projects` stores `{ type, id, title, appId, timestamp }`.

**Tracking points:**
- Chat session selected (`sessions.js` `selectSession()`)
- Document opened (`document.js` `openDocument()`)
- External app record viewed (app module calls `workspaceModule.recordProjectAccess(type, id, title, appId)`)

**UI:** Third row on Workspace:

```html
<div class="workspace-recent-projects">
  <span class="workspace-section-label">Recent Projects</span>
  <div class="recent-project-list">
    <button class="recent-project">
      <span class="project-type-icon">💬</span>
      <span class="project-name">Q4 Planning</span>
      <span class="project-app">Chat</span>
      <span class="project-time">2m ago</span>
    </button>
    ...
  </div>
</div>
```

### 8.4 Quick Launch

**Approach:** Extend the existing Ctrl+K global search (`search-chat.js`).

At L1, add a static app index to the search results:

```javascript
// In search-chat.js — add application source
const _appSearchResults = (query) => {
  const apps = [
    { id: 'maven-sync', name: 'MavenSync', keywords: 'sync share collaborate' },
    { id: 'hermes',     name: 'Hermes',     keywords: 'messages chat communicate' },
    { id: 'n8n',        name: 'n8n Workflows', keywords: 'automation workflow' },
    { id: 'ghl',        name: 'GoHighLevel',   keywords: 'crm sales contacts' },
  ];
  return apps
    .filter(a => a.name.toLowerCase().includes(q) || a.keywords.includes(q))
    .map(a => ({ type: 'app', appId: a.id, label: a.name }));
};
```

At L2, extend with a search source registry so each app can contribute dynamic results:

```javascript
const _searchSources = [];

export function registerSearchSource(source) {
  _searchSources.push(source);
  // source = { name, search(query): Promise<results[]> }
}

// Registered by each app module:
searchChatModule.registerSearchSource({
  name: 'Messages',
  search: async (q) => {
    const res = await fetch(`/api/hermes/search?q=${encodeURIComponent(q)}`);
    return (await res.json()).map(m => ({ type: 'message', id: m.id, label: m.subject }));
  }
});
```

Search popup groups results by source:

```
Conversations
  ─ Q4 Planning · 2 matches
  ─ Budget Review · 1 match

Messages
  ─ Alice: "Let's review Q4" · just now

Applications
  ─ n8n Workflows
  ─ GoHighLevel CRM
```

---

## 9. Sidebar Layout Recommendation

### Current Section Order

```
sidebar-brand
sidebar-new-chat
sidebar-search
── sessions-section (Chats)
── email-section
── models-section
── tools-section
  tool-memory (Brain)
  tool-calendar, tool-compare, tool-cookbook
  tool-research, tool-gallery, tool-library
  tool-notes, tool-tasks, tool-theme
sidebar-user-bar
```

### Recommended Section Order

```
sidebar-brand
sidebar-new-chat
sidebar-search
── workspace-section [NEW]
  tool-workspace (with aggregate notif dot)
── apps-section [NEW]
  tool-maven-sync
  tool-hermes
  tool-n8n
  tool-ghl
── sessions-section (Chats)
── email-section
── tools-section (existing Maven HQ tools)
  tool-memory, calendar, compare, cookbook
  tool-research, gallery, library
  notes, tasks, theme
── models-section
sidebar-user-bar
```

**The `apps-section` is for L1 launcher entries.** At L2, each app also gets a status dot and optional hover-preview on its sidebar item.

**Adding sections to codebase:**
1. Add `#workspace-section` and `#apps-section` to `static/index.html` within `.sidebar-inner`
2. Add to `section-management.js` for collapse/expand support
3. Add to `UI_VIS_MAP` for visibility control
4. Add to Appearance settings panel for user toggles

---

## 10. Global Search Integration Details

### Extending the existing Ctrl+K search

The current global search in `search-chat.js` handles:
- Opening overlay on Ctrl+K
- Debounced fetch to `GET /api/search?q=...`
- Keyboard-navigable results
- Session navigation on selection

**L1 changes (static app index):**

In `search-chat.js`, add a static app search that runs client-side along with the API search:

```javascript
// Merged into existing search flow
const _appResults = APPS.filter(a =>
  a.name.toLowerCase().includes(query) || a.keywords.includes(query)
);
// Rendered as a separate "Applications" group
```

**L2 changes (dynamic search sources):**

Add `registerSearchSource()` to the search module. Each app module registers during initialization:

```javascript
// search-chat.js
const _searchSources = [];
export function registerSearchSource(source) {
  _searchSources.push(source);
}
```

```javascript
// hermes.js — during init()
if (window.searchChatModule?.registerSearchSource) {
  window.searchChatModule.registerSearchSource({
    name: 'Messages',
    search: async (q) => {
      const res = await fetch(`/api/hermes/search?q=${encodeURIComponent(q)}`);
      return (await res.json()).map(m => ({
        type: 'message',
        id: m.id,
        label: m.subject,
        sublabel: m.preview,
      }));
    },
  });
}
```

The search overlay renders groups with dividers. Selecting a result:
- **App type:** `workspaceModule.openApp(appId)`
- **Message type:** Deep-link to Hermes conversation
- **Chat/document type:** Existing behavior (unchanged)

---

## 11. Dynamic App Registry

Replace the hardcoded `_routeOpen`, `_railToolMap`, `UI_VIS_MAP`, and keyboard shortcut maps with a **dynamic app registry**:

```javascript
// workspace.js — app registry
const _apps = new Map();

export function registerApp(config) {
  _apps.set(config.id, config);
  // config = {
  //   id: 'maven-sync',
  //   name: 'MavenSync',
  //   icon: '<svg>...</svg>',
  //   open: () => { /* new-tab, iframe, or native open */ },
  //   level: 'launcher',        // 'launcher' | 'connected' | 'embedded'
  //   sidebarSelector: '#tool-maven-sync-btn',
  //   railId: 'rail-maven-sync',
  //   railLabel: 'Sync',
  //   settingsKey: 'tool-maven-sync',
  //   keyboardShortcut: 'ctrl+alt+s',
  //   notifDotSelector: '#sync-notif-dot',
  //   searchSource: { name: 'Sync', search: async (q) => [...] },
  //   statusEndpoint: '/api/maven-sync/status',
  // }
}
```

At boot, `app.js` iterates `_apps` and wires:
- Sidebar click handler → `config.open()`
- Icon rail `_railToolMap` entry → sidebar delegation
- `UI_VIS_MAP` entry → visibility toggle
- Keyboard shortcut → `_defaultKeybinds`
- Search source → `searchChatModule.registerSearchSource()`
- Status polling → `registerAppStatus()`

**Backend app discovery (future):**

```json
GET /api/apps
[
  {
    "id": "maven-sync",
    "name": "MavenSync",
    "launchUrl": "https://sync.mavenhq.local",
    "level": "launcher",
    "icon": "sync",
    "enabled": true
  }
]
```

The frontend iterates this list at boot and calls `registerApp()` for each entry, enabling zero-code app addition.

---

## 12. Phased Implementation Table

### Phase 1 — Launch Version

| App | L1 Tasks | Effort |
|---|---|---|
| **All** | Dynamic app registry in `workspace.js` | Medium |
| **All** | Workspace page with favorites + recents | Medium |
| **All** | `#apps-section` sidebar section | Small |
| **All** | Ctrl+K search extension (static app index) | Small |
| **MavenSync** | Launcher card + sidebar entry + new-tab launch | Small |
| **Hermes** | Launcher card + sidebar entry + new-tab launch | Small |
| **OmniRoute** | Settings tab + chat top-bar status dot | Small |
| **n8n** | Launcher card + sidebar entry + new-tab launch | Small |
| **GoHighLevel** | Launcher card + sidebar entry + new-tab launch + deep-link patterns | Small |

**Total phase 1 effort:** ~2–3 weeks (single developer). Core Workspace framework + all 5 apps at L1.

### Phase 2 — Connected Version

| App | L2 Tasks | Effort |
|---|---|---|
| **All** | Centralized notification bus + status polling framework | Medium |
| **All** | `searchChatModule.registerSearchSource()` API | Small |
| **MavenSync** | Status API proxy + sidebar dot + recent activity on Workspace card | Medium |
| **Hermes** | Unread count proxy + sidebar badge + recent messages preview | Medium |
| **OmniRoute** | Health polling + route table in settings + failure toasts | Small |
| **n8n** | Workflow status proxy + sidebar badge on failure | Medium |
| **GoHighLevel** | Pipeline summary proxy + sidebar badge + quick actions | Medium |

**Total phase 2 effort:** ~2–3 weeks.

### Phase 3 — Advanced Embedded Version

| App | L3 Tasks | Effort | Risk |
|---|---|---|---|
| **MavenSync** | Validate `X-Frame-Options`, CSP, cookie sharing. Fullscreen iframe if viable. | Medium | Low (controlled service) |
| **Hermes** | Quick-prompt iframe or side panel. Requires Hermes to expose an embeddable compose view. | Medium | Medium |
| **n8n** | Full iframe modal. Must validate n8n embedding headers. Proxy auth. | Medium | High (third-party, config varies) |
| **GoHighLevel** | Full iframe modal. Almost certainly blocked by `X-Frame-Options`. Low priority. | Low effort (it won't work) | Very high (SaaS restrictions) |

**Start phase 3 only after users validate phase 1 and 2 in production.**

---

## 13. Merge Conflict Mitigation

| Risk | Mitigation |
|---|---|
| **Sidebar HTML changes** | Keep external app entries in a single contiguous block within `#apps-section` with clear comments `<!-- BEGIN EXTERNAL APPS -->` / `<!-- END EXTERNAL APPS -->` |
| **`UI_VIS_MAP` conflicts** | Group external app entries in an `_EXTERNAL_APP_KEYS` object merged into `UI_VIS_MAP` at runtime via `Object.assign()` |
| **`_railToolMap` conflicts** | Add external app entries via `Object.assign(_railToolMap, externalAppMap)` instead of inline entries |
| **Keyboard shortcut conflicts** | Generate external app shortcuts dynamically from the registry; keep them in a separate `externalShortcuts` object |
| **Search source conflicts** | Each app registers its search source independently via `registerSearchSource()` — no central file to edit |
| **CSP updates** | Maintain a single `ALLOWED_FRAME_SRC` list in `app.py`'s `SecurityHeadersMiddleware` for all embeddable apps |

---

## 14. Summary

| App | L1 (Launch) | L2 (Connected) | L3 (Embedded) | Priority |
|---|---|---|---|---|
| **MavenSync** | New-tab launcher + sidebar | Status dot + recent activity + conflict count | Fullscreen iframe (if viable) | High |
| **Hermes** | New-tab launcher + sidebar + deep links | Unread badge + recent messages preview | Quick-prompt side panel (if viable) | High |
| **OmniRoute** | Settings tab + top-bar dot | Health polling + route table in settings | N/A | High |
| **n8n** | New-tab launcher + sidebar | Workflow status badge + error counts | Fullscreen iframe (after validation) | Medium |
| **GoHighLevel** | New-tab launcher + sidebar + deep links | Pipeline summary + new-lead badge | Fullscreen iframe (low priority, likely blocked) | Medium |

**Foundation work (phase 1 prerequisite):** Dynamic app registry, Workspace landing page, `#apps-section` sidebar section, Ctrl+K search extension, centralized notification bus.
