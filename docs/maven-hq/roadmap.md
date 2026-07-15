# Implementation Roadmap — Maven HQ

## Executive Summary

This roadmap synthesizes the branding audit, theme analysis, workspace design, and integration plan into five implementation phases. The recommended order minimizes risk by establishing the branding foundation first, then the workspace landing page, then external app integration, then advanced features.

| Phase | Name | Effort | Dependencies | Risk | Sessions |
|---|---|---|---|---|---|
| 1 | Branding Foundation | Medium | None | Low | 3–4 |
| 2 | Workspace Landing Page | Medium | None | Low | 2–3 |
| 3 | App Registry & Launcher Integration | Medium | Phase 2 | Low | 2–3 |
| 4 | Connected Status & Notifications | Medium | Phase 3 | Medium | 2–3 |
| 5 | Refinement & Embedded Validation | Variable | Phase 4 | High | 2–4 |

**Total estimated effort:** 11–17 sessions for a single developer.

### High-Risk Items
- **Phase 5 (L3 iframe embedding):** Dependent on third-party `X-Frame-Options`, CSP, and cookie policies. May be impossible for GoHighLevel. Must validate before committing.
- **Phase 1 cookie rename (`odysseus_session` → `maven_hq_session`):** Breaks all existing sessions. Must coordinate with all users to re-authenticate.
- **Phase 2 login redirect change:** Users who bookmark `/` will land on Workspace instead of Chat. Mitigate with a user preference toggle before rolling out.

### Quick Wins
- Phase 1 CSS override layer (`static/maven-hq-brand.css`) — changes the entire app's color scheme with zero risk.
- Phase 1 brand config module (`static/js/maven-hq-branding.js`) — centralizes all brand text for future changes.
- Phase 3 L1 launchers — add all 5 external apps with ~30 lines of code each.

### Deferred Features
- P2P/WebRTC voice/video integration (not in scope unless an external app provides it)
- Custom widget system for the Workspace (drag-and-drop dashboard builder)
- Native mobile app (electron/tauri bundling)
- Multi-user workspace layouts (shared workspaces)

---

## Phase 1 — Branding Foundation

**Goal:** Replace all "Odysseus" references with "Maven HQ" identity. Establish centralized branding layer so all future branding changes require editing only 3 files.

### Deliverables

| # | Task | File(s) | Complexity |
|---|---|---|---|
| 1.1 | Create `static/maven-hq-brand.css` — CSS variable override layer loaded after `style.css` | New file | Small |
| 1.2 | Create `static/js/maven-hq-branding.js` — centralized brand config (name, logo SVG, route titles, color defaults) | New file | Small |
| 1.3 | Create `src/maven_hq_branding.py` — centralized backend brand constants (cookie name, TOTP issuer, backup prefix, headers, env prefix) | New file | Small |
| 1.4 | Update `static/index.html` — `<title>`, route titles, sidebar brand text, welcome text, AIO heading, chat meta text, settings labels, favicon SVG data URI, logo SVG in welcome screen | `static/index.html` | Medium |
| 1.5 | Update `static/login.html` — `<title>`, logo SVG, brand text, favicon SVG data URI | `static/login.html` | Small |
| 1.6 | Update `static/manifest.json` — `name`, `short_name`, `description`, `background_color`, `theme_color` | `static/manifest.json` | Small |
| 1.7 | Update `static/sw.js` — cache name string | `static/sw.js` | Small |
| 1.8 | Update `static/js/theme.js` — `ADV_KEYS` brand label, favicon fallback SVG shape | `static/js/theme.js` | Small |
| 1.9 | Update `launcher.py` — splash text, window title, tray name, tray icon drawing (Pillow polygons → Maven HQ logo) | `launcher.py` | Medium |
| 1.10 | Update `Odysseus.spec` — EXE name, spec filename | `Odysseus.spec` | Small |
| 1.11 | Replace icon assets — `static/icon.ico`, `static/icons/icon-192.png`, `static/icons/icon-512.png`, `static/icons/icon-maskable-512.png` | Static assets | Small |
| 1.12 | Update `docs/index.html` — `<title>`, favicon SVGs, logo SVGs, brand text | `docs/index.html` | Small |
| 1.13 | Update `routes/auth_routes.py` — session cookie name (`odysseus_session` → `maven_hq_session`) | `routes/auth_routes.py` | Small |
| 1.14 | Update `core/auth.py` — TOTP issuer name | `core/auth.py` | Small |
| 1.15 | Update `routes/backup_routes.py` — backup filename prefix | `routes/backup_routes.py` | Small |
| 1.16 | Update `core/middleware.py` — internal header names, env var names | `core/middleware.py` | Small |
| 1.17 | Update `app.py` — env var names (`ODYSSEUS_*` → `MAVEN_HQ_*`), internal header names | `app.py` | Medium |
| 1.18 | Update `routes/email_routes.py` — header names (`X-Odysseus-*` → `X-Maven-HQ-*`) | `routes/email_routes.py` | Small |
| 1.19 | Replace docs images — `docs/odysseus-wordmark.png`, `docs/odysseus.jpg`, `docs/odysseus-browser.jpg` | Docs assets | Small |
| 1.20 | Verify: no remaining "Odysseus" references in user-facing surfaces | All | Verification |

### Verification Checklist
- [ ] Browser tab shows "Maven HQ" (not "Odysseus") at every route
- [ ] Login page shows Maven HQ branding, logo, favicon
- [ ] Sidebar shows "Maven HQ" brand text
- [ ] Welcome screen shows Maven HQ logo and name
- [ ] Settings panel labels reference Maven HQ
- [ ] PWA manifest reports "Maven HQ"
- [ ] Service worker cache name is `maven-hq-v1`
- [ ] System tray icon shows Maven HQ logo with "Maven HQ" tooltip
- [ ] PyInstaller builds produce `MavenHQ.exe`
- [ ] TOTP issuer in authenticator app shows "Maven HQ"
- [ ] Backup files are named `maven_hq_backup_*`
- [ ] Email headers show `X-Maven-HQ-*`
- [ ] Docs site uses Maven HQ branding throughout
- [ ] Session cookie is named `maven_hq_session` (all users must re-authenticate)
- [ ] No user-facing "Odysseus" text exists in HTML/JS/Python surfaces

### Risks & Mitigation
| Risk | Mitigation |
|---|---|
| Session cookie rename forces re-authentication | Communicate to all users before deployment. Perform during scheduled maintenance. |
| Env var rename (`ODYSSEUS_*` → `MAVEN_HQ_*`) breaks deployed configs | Update deployment configs first, then deploy code change. Use a fallback period where both names are checked. |
| `launcher.py` Pillow icon drawing is non-trivial | Sketch Maven HQ logo as SVG path first, then translate to Pillow polygon coordinates. |

---

## Phase 2 — Workspace Landing Page

**Goal:** Create a `/workspace` top-level SPA route with a fullscreen landing page that serves as the user's home base after login.

### Deliverables

| # | Task | File(s) | Complexity |
|---|---|---|---|
| 2.1 | Register `GET /workspace` server route serving `index.html` | `app.py` | Small |
| 2.2 | Register `/workspace` in client-side `_routeOpen` map | `static/app.js` | Small |
| 2.3 | Add favicon/title customization entry for `/workspace` | `static/index.html` inline script | Small |
| 2.4 | Create `static/js/workspace.js` module (open/close/toggle with sidebar collapse) | New file | Medium |
| 2.5 | Add workspace-panel HTML to `index.html` (hidden by default) | `static/index.html` | Small |
| 2.6 | Add workspace-panel CSS (fullscreen overlay with icon-rail margin) | `static/style.css` | Medium |
| 2.7 | Add sidebar list-item for Workspace navigation | `static/index.html` sidebar | Small |
| 2.8 | Add icon-rail button for Workspace | `static/index.html` icon rail | Small |
| 2.9 | Wire rail-to-tool mapping for workspace button | `static/app.js` | Small |
| 2.10 | Register click handler in `initializeEventListeners()` | `static/app.js` | Small |
| 2.11 | Add visibility toggle in Appearance settings panel | `static/index.html` Appearance panel | Small |
| 2.12 | Change login redirect to `/workspace` (or add first-visit check) | `static/login.html` | Small |
| 2.13 | Guard welcome screen functions against workspace open | `static/js/chatRenderer.js`, `static/js/sessions.js` | Small |
| 2.14 | Add Workspace API endpoints (recent sessions, pinned tools, system status) | `routes/workspace_routes.py` | Medium |
| 2.15 | Add user preference: "Default landing page: Chat / Workspace" | `static/index.html` Settings, `routes/prefs_routes.py` | Small |

### Verification Checklist
- [ ] Navigating to `/workspace` loads the Workspace panel
- [ ] Sidebar collapses to icon rail when Workspace opens
- [ ] Workspace close button restores sidebar and returns to previous view
- [ ] Login redirect lands on Workspace (or Chat based on user preference)
- [ ] Workspace shows recent sessions, pinned tools, system status
- [ ] Bookmarking `/workspace` works on direct navigation
- [ ] Welcome screen does not conflict with Workspace panel
- [ ] Appearance settings include Workspace visibility toggle
- [ ] Service worker caches `/workspace` route correctly (same `index.html` shell)

### Dependencies
- Phase 1 must be complete (branding layer exists for Workspace header/title)

### Risks & Mitigation
| Risk | Mitigation |
|---|---|
| Workspace panel conflicts with existing welcome screen logic | Guard all `hideWelcomeScreen`/`showWelcomeScreen` calls with `workspaceModule.isOpen()` check |
| Users expect Chat as default landing | Add user preference toggle before changing login redirect |

---

## Phase 3 — App Registry & Launcher Integration (L1)

**Goal:** Create a dynamic app registry system and implement L1 (launcher) integration for all five external applications.

### Deliverables

| # | Task | File(s) | Complexity |
|---|---|---|---|
| 3.1 | Build dynamic app registry in `workspace.js` — `registerApp(config)` with wiring for sidebar, rail, keyboard shortcuts, search, status polling | `static/js/workspace.js` | Medium |
| 3.2 | Create workspace-panel HTML structure: favorites row, recent apps row, recent projects row | `static/index.html` workspace panel | Medium |
| 3.3 | Add `#apps-section` sidebar section (between workspace and sessions) | `static/index.html` sidebar | Small |
| 3.4 | Add collapse/expand support for `#apps-section` in section management | `static/js/section-management.js` | Small |
| 3.5 | Add `#apps-section` to `UI_VIS_MAP` for visibility control | `static/app.js` | Small |
| 3.6 | Extend Ctrl+K search with static app index (client-side, L1) | `static/js/search-chat.js` | Small |
| 3.7 | Create `static/js/maven-sync.js` — L1 launcher (new-tab launch) | New file | Small |
| 3.8 | Create `static/js/hermes.js` — L1 launcher (new-tab launch + deep-link patterns) | New file | Small |
| 3.9 | Create `static/js/n8n.js` — L1 launcher (new-tab launch) | New file | Small |
| 3.10 | Create `static/js/gohighlevel.js` — L1 launcher (new-tab launch + deep-link patterns) | New file | Small |
| 3.11 | Register all 4 app modules via `registerApp()` at boot | `static/js/app.js` | Small |
| 3.12 | Add app launcher cards to Workspace panel (tile with icon, name, status dot) | `static/index.html` workspace panel | Medium |
| 3.13 | Add workspace favorites management (right-click sidebar → add to favorites, drag-to-reorder, 8-app limit) | `static/js/workspace.js` | Medium |
| 3.14 | Add workspace recents tracking (localStorage, max 10 entries) | `static/js/workspace.js` | Small |
| 3.15 | Add recently opened projects tracking (chat sessions, documents, external app records) | `static/js/workspace.js`, `static/js/sessions.js`, `static/js/document.js` | Medium |
| 3.16 | Implement backend app discovery endpoint (`GET /api/apps`) | `routes/workspace_routes.py` | Small |
| 3.17 | OmniRoute: Add settings tab + chat top-bar status dot (infrastructure, not a launcher) | `static/index.html`, `static/js/workspace.js` | Small |

### Verification Checklist
- [ ] All 4 external app launchers open the correct URL in a new tab
- [ ] Sidebar `#apps-section` shows all 4 apps with correct labels and icons
- [ ] Workspace panel shows favorite apps row (configurable, max 8)
- [ ] Workspace panel shows recent apps row (up to 10)
- [ ] Workspace panel shows recent projects row
- [ ] Ctrl+K search includes "Applications" group with all 4 apps
- [ ] Deep-link patterns work for Hermes and GoHighLevel
- [ ] OmniRoute settings tab appears in Settings modal
- [ ] OmniRoute chat top-bar status dot appears (gray at L1)
- [ ] Favorites persist across page reloads
- [ ] Recents update on each app launch
- [ ] `GET /api/apps` returns the correct app list
- [ ] Right-click sidebar tool → "Add to Workspace favorites" works

### Dependencies
- Phase 2 must be complete (Workspace panel structure exists)

### Risks & Mitigation
| Risk | Mitigation |
|---|---|
| App registry conflicts with existing `_routeOpen`, `_railToolMap`, `UI_VIS_MAP` | Use `Object.assign()` for merge; keep external entries in clearly marked blocks |
| Sidebar HTML merge conflicts | Keep external app entries in contiguous `<!-- BEGIN EXTERNAL APPS -->` / `<!-- END EXTERNAL APPS -->` blocks |

---

## Phase 4 — Connected Status & Notifications (L2)

**Goal:** Add L2 connected features — API-driven status indicators, recent activity previews, quick actions, and a centralized notification bus.

### Deliverables

| # | Task | File(s) | Complexity |
|---|---|---|---|
| 4.1 | Build centralized notification bus using `CustomEvent` — listen for `odysseus:app-notification`, aggregate counts, show toasts | `static/js/workspace.js` | Medium |
| 4.2 | Build generic status polling framework — `registerAppStatus(appId, { endpoint, interval, onStatus })` | `static/js/workspace.js` | Medium |
| 4.3 | Implement `searchChatModule.registerSearchSource()` API for dynamic search | `static/js/search-chat.js` | Small |
| 4.4 | **MavenSync L2:** Status API proxy (`GET /api/maven-sync/status`) + sidebar status dot (green/gray/red) + recent activity on Workspace card + "Sync now" quick action | `routes/proxy_routes.py`, `static/js/maven-sync.js` | Medium |
| 4.5 | **Hermes L2:** Unread count proxy (`GET /api/hermes/unread`) + sidebar notification badge + recent messages preview on Workspace card + "Compose" quick action | `routes/proxy_routes.py`, `static/js/hermes.js` | Medium |
| 4.6 | **n8n L2:** Workflow status proxy (`GET /api/n8n/workflow-status`) + sidebar badge on failure + active/failed counts on Workspace card + "Retry Failed" quick action | `routes/proxy_routes.py`, `static/js/n8n.js` | Medium |
| 4.7 | **GoHighLevel L2:** Pipeline summary proxy (`GET /api/ghl/pipeline-summary`) + sidebar badge for new leads + pipeline summary widget on Workspace card + "New Contact" and "View Pipeline" quick actions | `routes/proxy_routes.py`, `static/js/gohighlevel.js` | Medium |
| 4.8 | **OmniRoute L2:** Health polling (`GET /api/routing/health`) + route table in settings panel + latency display + failure/recovery toasts | `routes/routing_routes.py`, `static/js/omniroute.js` | Small |
| 4.9 | Register all L2 status pollers via `registerAppStatus()` during boot | `static/js/workspace.js` | Small |
| 4.10 | Register all L2 search sources via `registerSearchSource()` | Each app module | Small |
| 4.11 | Add webhook receiver endpoints for push notifications (where applicable) | `routes/webhook_routes.py` | Medium |
| 4.12 | Implement notification badge on workspace aggregate (top-right Workspace sidebar entry) | `static/js/workspace.js` | Small |

### Verification Checklist
- [ ] Each app's sidebar entry shows correct status dot/badge
- [ ] Status dots update at the configured interval (30s default)
- [ ] Status dots gracefully show "disconnected" on API failure
- [ ] Workspace cards show relevant preview data (recent activity, workflow status, pipeline summary)
- [ ] Quick action buttons launch the correct URLs or trigger correct API calls
- [ ] Notifications from external apps appear as toasts
- [ ] Aggregate notification badge on Workspace sidebar entry shows correct total
- [ ] Ctrl+K search returns dynamic results from registered apps
- [ ] All API keys stored server-side via `/api/prefs`, never exposed to frontend
- [ ] OmniRoute settings panel shows route table and latency

### Dependencies
- Phase 3 must be complete (app registry, sidebar entries, Workspace cards exist)

### Risks & Mitigation
| Risk | Mitigation |
|---|---|
| External API rate limits | Use appropriate polling intervals (30s-60s). Cache responses on backend. |
| API key exposure | Proxy pattern keeps keys server-side; frontend never sees them |
| Webhook reliability | Use retry + idempotency keys for webhook delivery |

---

## Phase 5 — Refinement & Embedded Validation (L3)

**Goal:** Validate and implement L3 embedded experiences where technically viable. Polish all phases.

### Deliverables

| # | Task | File(s) | Complexity |
|---|---|---|---|
| 5.1 | **MavenSync L3 validation:** Check `X-Frame-Options`, CSP `frame-ancestors`, cookie SameSite, CORS headers | MavenSync deployment | Small |
| 5.2 | **MavenSync L3 implementation:** Fullscreen iframe embed (if viable) with auth token passthrough | `static/js/maven-sync.js` | Medium |
| 5.3 | **Hermes L3 validation:** Check if Hermes has a dedicated embeddable compose/quick-send view | Hermes deployment | Small |
| 5.4 | **Hermes L3 implementation:** Quick-prompt side panel iframe (docked right, notes-panel pattern) | `static/js/hermes.js`, CSS | Medium |
| 5.5 | **n8n L3 validation:** Check n8n embedding headers, test iframe loading, verify auth | n8n deployment | Small |
| 5.6 | **n8n L3 implementation:** Full iframe modal with proxy auth | `static/js/n8n.js` | Medium |
| 5.7 | **GoHighLevel L3 validation:** Confirm `X-Frame-Options` status (almost certainly blocked) | GHL deployment | Small |
| 5.8 | **GoHighLevel L3:** Document the blocking issue, recommend sticking with L1+L2 | Documentation | Small |
| 5.9 | Add CSP `frame-src` entries to `SecurityHeadersMiddleware` for all validated embeddable apps | `app.py` | Small |
| 5.10 | Performance audit: lazy-load app modules, optimize status polling, minimize reflows | All app modules | Medium |
| 5.11 | Accessibility audit: keyboard navigation, screen reader labels, focus management | Workspace panel, app modules | Medium |
| 5.12 | Error handling polish: offline mode, graceful degradation, retry logic | All app modules | Medium |
| 5.13 | User documentation: Workspace usage guide, app integration setup | `docs/` | Medium |

### Verification Checklist
- [ ] Validated `X-Frame-Options` and CSP for each candidate embed app
- [ ] Documented which apps support embedding and which do not
- [ ] Maven Sync iframe loads and functions correctly (if viable)
- [ ] Hermes quick-prompt side panel loads (if viable)
- [ ] n8n iframe modal works with auth (if viable)
- [ ] GoHighLevel embedding status documented
- [ ] CSP `frame-src` includes only validated origins
- [ ] All app modules lazy-load on first use (not at boot)
- [ ] Keyboard navigation works for all Workspace panel interactions
- [ ] Screen reader labels present on all app cards and sidebar entries
- [ ] Offline mode shows cached status (last known state)
- [ ] Error states show helpful messages, not blank panels

### Dependencies
- Phase 4 must be complete (L2 features validated in production by users)
- User feedback from Phases 3–4 should guide L3 priority

### Risks & Mitigation
| Risk | Mitigation |
|---|---|
| GoHighLevel blocks embedding (highly likely) | Accept L1+L2 as final state. Document. |
| n8n embedding breaks after update | Pin n8n version. Add regression test. |
| iframe auth is fragile | Prefer L1+L2 over fragile L3. User can always open in new tab. |
| Performance regression from iframes | Lazy-load iframes only on user click. Destroy iframe on close. |

---

## Appendix A: Dependency Graph

```
Phase 1 (Branding Foundation)
  └── No dependencies
Phase 2 (Workspace Landing Page)
  └── Requires Phase 1 (brand name/title correct in Workspace)
Phase 3 (App Registry & Launcher)
  └── Requires Phase 2 (Workspace panel exists)
Phase 4 (Connected Status)
  └── Requires Phase 3 (app registry, sidebar entries, cards)
Phase 5 (Embedded & Polish)
  └── Requires Phase 4 (L2 validated in production)
```

## Appendix B: File Change Summary by Phase

| File | P1 | P2 | P3 | P4 | P5 |
|---|---|---|---|---|---|
| `static/maven-hq-brand.css` | NEW | — | — | — | — |
| `static/js/maven-hq-branding.js` | NEW | — | — | — | — |
| `src/maven_hq_branding.py` | NEW | — | — | — | — |
| `static/js/workspace.js` | — | NEW | EDIT | EDIT | EDIT |
| `static/js/maven-sync.js` | — | — | NEW | EDIT | EDIT |
| `static/js/hermes.js` | — | — | NEW | EDIT | EDIT |
| `static/js/n8n.js` | — | — | NEW | EDIT | — |
| `static/js/gohighlevel.js` | — | — | NEW | EDIT | — |
| `static/js/omniroute.js` | — | — | NEW | EDIT | — |
| `static/index.html` | EDIT | EDIT | EDIT | — | — |
| `static/login.html` | EDIT | EDIT | — | — | — |
| `static/app.js` | — | EDIT | EDIT | — | — |
| `static/js/theme.js` | EDIT | — | — | — | — |
| `static/js/search-chat.js` | — | — | EDIT | EDIT | — |
| `static/manifest.json` | EDIT | — | — | — | — |
| `static/sw.js` | EDIT | — | — | — | — |
| `static/style.css` | — | EDIT | — | — | EDIT |
| `launcher.py` | EDIT | — | — | — | — |
| `Odysseus.spec` | EDIT | — | — | — | — |
| `app.py` | EDIT | EDIT | — | — | EDIT |
| `routes/auth_routes.py` | EDIT | — | — | — | — |
| `core/auth.py` | EDIT | — | — | — | — |
| `routes/backup_routes.py` | EDIT | — | — | — | — |
| `core/middleware.py` | EDIT | — | — | — | — |
| `routes/email_routes.py` | EDIT | — | — | — | — |
| `routes/workspace_routes.py` | — | EDIT | EDIT | — | — |
| `routes/proxy_routes.py` | — | — | — | NEW | — |
| `routes/webhook_routes.py` | — | — | — | NEW | — |
| `routes/routing_routes.py` | — | — | — | NEW | — |
| `docs/index.html` | EDIT | — | — | — | — |
| Icon assets (6 files) | EDIT | — | — | — | — |
| Docs images (3 files) | EDIT | — | — | — | — |

## Appendix C: Rollback Strategy

| Phase | Rollback Action |
|---|---|
| 1 | Revert branding files, restore icon assets, revert env var rename, restore cookie name (requires re-auth) |
| 2 | Revert `/workspace` route registration, login redirect, sidebar/rail entries |
| 3 | Remove `#apps-section`, revert app registry, unregister app modules, remove workspace cards |
| 4 | Disconnect status polling, remove proxy routes, disable notification bus |
| 5 | Remove iframe modals, revert CSP changes, restore side panel |
