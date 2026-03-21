# Touch-Responsive Device Tiers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add pointer-based CSS device tiers so iPads get a touch-optimized tablet UI instead of the desktop layout.

**Architecture:** Replace width-only breakpoints with `pointer: coarse`/`pointer: fine` media queries. Shared touch rules apply to all touch devices; width sub-breakpoints distinguish phone from tablet layout density. New utility classes (`touch-only`, `touch-large-only`, `not-phone`) give granular per-component visibility control.

**Tech Stack:** CSS media queries, NiceGUI/Python class attributes

**Spec:** `docs/superpowers/specs/2026-03-21-touch-responsive-tiers-design.md`

**Conflict note:** `src/ui/positions.py` is currently being modified by another instance. Task 4 (positions class swap) should be deferred if the file is still dirty when reached. Check `git status` before starting that task.

---

### Task 1: Add new utility class definitions and redefine desktop-only/mobile-only

The foundation — define all utility classes so they can be used immediately.

**Files:**
- Modify: `src/theme.py:360-362` (utility class defaults)

- [ ] **Step 1: Replace the current mobile-only/desktop-only defaults with the full set of utility classes**

Find the block at lines 360-362:
```css
/* ── Mobile utility classes ── */
.mobile-only { display: none !important; }
.desktop-only { /* visible by default; hidden via media query on mobile */ }
```

Replace with:
```css
/* ── Device-tier utility classes ── */
.mobile-only { display: none !important; }
.desktop-only { /* visible by default; hidden via pointer queries */ }
.touch-only { display: none !important; }
.touch-large-only { display: none !important; }
.not-phone { /* visible by default; hidden on touch-small */ }
```

- [ ] **Step 2: Verify no syntax errors**

Run: `cd "/Users/joakimhersche/Documents/Python Project/market-dashboard" && python -c "import src.theme; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/theme.py
git commit -m "feat: add touch-only, touch-large-only, not-phone utility classes"
```

---

### Task 2: Create the shared touch tier — `@media (pointer: coarse)`

Move shared mobile/touch rules out of the `max-width: 767px` block into a pointer-based query. Merge with the existing `pointer: coarse` touch-target block (lines 660-667).

**Files:**
- Modify: `src/theme.py:395-646` (the `max-width: 767px` block)
- Modify: `src/theme.py:660-667` (existing `pointer: coarse` block)

- [ ] **Step 1: Replace the existing `@media (pointer: coarse)` block (lines 660-667) with the full shared touch tier**

Replace the existing block:
```css
/* ── Touch-friendly targets ───────────────────────────── */
@media (pointer: coarse) {
  .pill { padding: 6px 12px; font-size: 11px; }
  .add-btn { padding: 10px 0; font-size: 12px; }
  .sidebar-btn { padding: 10px 0; font-size: 12px; }
  .position-row { padding: 8px 6px; }
  .q-btn-toggle .q-btn { min-height: 44px !important; min-width: 44px !important; }
  .position-row .q-btn { opacity: 1 !important; min-width: 32px !important; min-height: 32px !important; }
}
```

With the expanded shared touch tier:
```css
/* ── Shared touch tier (all touch devices) ────────────── */
@media (pointer: coarse) {
  /* Touch targets */
  .pill { padding: 6px 12px; font-size: 11px; }
  .add-btn { padding: 10px 0; font-size: 12px; }
  .sidebar-btn { padding: 10px 0; font-size: 12px; }
  .position-row { padding: 8px 6px; }
  .q-btn-toggle .q-btn { min-height: 44px !important; min-width: 44px !important; }
  .position-row .q-btn { opacity: 1 !important; min-width: 32px !important; min-height: 32px !important; }

  /* Utility classes: show touch, hide desktop */
  .touch-only { display: block !important; }
  .desktop-only { display: none !important; }

  /* Bottom tab bar visible */
  .mobile-tab-bar { display: flex !important; }

  /* Hide top tab bar */
  .tab-bar-wrapper {
    position: absolute !important;
    opacity: 0 !important;
    pointer-events: none !important;
    height: 1px !important;
    overflow: hidden !important;
    z-index: -1 !important;
  }
  .tab-bar-wrapper::after { display: none !important; }

  /* Body padding for fixed bottom bar */
  .q-page, .nicegui-content {
    padding-bottom: calc(72px + env(safe-area-inset-bottom, 0px)) !important;
  }

  /* Header: show hamburger, hide desktop controls */
  .hamburger-btn {
    display: flex !important;
    min-width: 44px !important;
    min-height: 44px !important;
    color: #F1F5F9 !important;
    opacity: 1 !important;
  }
  .hamburger-btn .q-icon { font-size: 24px !important; }
  .header-export-btn { display: none !important; }
  .header-info-btn { display: none !important; }
  .header-currency-pills { display: none !important; }

  /* Topbar: safe area for standalone PWA */
  .q-header {
    padding-left: 8px !important;
    padding-right: 8px !important;
    padding-top: env(safe-area-inset-top, 0px) !important;
    min-height: calc(48px + env(safe-area-inset-top, 0px)) !important;
  }

  /* Disable sidebar edge-swipe; prevent closed drawer from blocking touches */
  .q-drawer__backdrop { touch-action: none !important; }
  .q-drawer--left { touch-action: none !important; }
  .q-drawer-container { pointer-events: none !important; }
  .q-drawer--opened { pointer-events: auto !important; }
  .q-drawer__backdrop[style*="display: block"] { pointer-events: auto !important; }

  /* Sidebar backdrop */
  .q-drawer__backdrop {
    background: rgba(0, 0, 0, 0.5) !important;
  }

  /* Tab panels: reduce padding */
  .q-tab-panels, .q-tab-panel { padding: 12px !important; }

  /* Tabs: scroll horizontally */
  .q-tabs { overflow-x: auto; }
  .q-tab { font-size: 11px !important; min-width: auto !important; padding: 0 10px !important; }

  /* Sidebar buttons: touch-friendly */
  .sidebar .q-btn, .sidebar .sidebar-btn {
    min-height: 40px !important;
    font-size: 13px !important;
  }

  /* Sidebar: ensure touch-only elements render */
  .q-drawer .touch-only { display: block !important; visibility: visible !important; }

  /* Plotly: hide modebar on touch */
  .modebar-container { display: none !important; }
  .js-plotly-plot, .plotly { width: 100%% !important; }
  .js-plotly-plot .main-svg { width: 100%% !important; }

  /* Prevent iOS zoom on input focus */
  input, select, textarea,
  .q-field__native, .q-field__input, .q-select__input,
  .q-header .q-field__native,
  .sidebar .q-field__native, .sidebar .q-field__input {
    font-size: 16px !important;
  }

  /* Sidebar section headers */
  .sidebar-section-header { font-size: 10px; }
}
```

- [ ] **Step 2: Remove the duplicated rules from the `@media (max-width: 767px)` block**

The following rules were moved to the shared touch tier and must be removed from the `@media (max-width: 767px)` block. Remove these specific rule groups (keep the rest — phone-only layout rules stay):

Remove these rules (now in the shared touch tier — identify by CSS selector content, not line numbers):
- `.mobile-tab-bar { display: flex !important; }`
- `.tab-bar-wrapper { position: absolute ... }` block and `::after`
- `.q-page, .nicegui-content { padding-bottom: calc(72px + ...) }`
- `.hamburger-btn { display: flex ... }` block and `.hamburger-btn .q-icon`
- `.header-export-btn`, `.header-info-btn`, `.header-currency-pills` hide rules
- `.q-header { padding-left: 8px ... }` topbar padding block
- `.q-drawer__backdrop { touch-action: ... }`, `.q-drawer--left`, `.q-drawer-container`, `.q-drawer--opened`, `.q-drawer__backdrop[style*=...]`
- `.q-drawer__backdrop { background: rgba(0,0,0,0.5) }`
- `.q-tab-panels, .q-tab-panel { padding: 12px }`
- `.q-tabs { overflow-x: auto }` and `.q-tab { font-size: 11px ... }`
- `.sidebar .q-btn, .sidebar .sidebar-btn { min-height: 40px }` (search for this exact rule — it may be in a different location than expected)
- `.q-drawer .mobile-only { display: block ... visibility: visible }` — replaced by `.q-drawer .touch-only` in shared tier
- `.sidebar-section-header { font-size: 10px }`
- `.modebar-container { display: none }` and Plotly width rules
- `input, select, textarea ... { font-size: 16px }` iOS zoom prevention
- `.desktop-only { display: none !important; }` — now in shared tier

Keep in the block (phone-specific layout):
- `.q-drawer { width: 100vw }` — full-width sidebar
- `.q-drawer .sidebar { padding ... }` — sidebar padding
- `.q-drawer .sidebar .sidebar-bottom-actions { ... }` — sticky bottom
- `.q-drawer .sidebar .q-field { margin-bottom: 0 }` — field margin
- `.sidebar-currency-pills` rules (will be moved to shared tier in Task 6)
- `.kpi-row { flex-direction: column }` and KPI single-column rules
- `.charts-row { grid-template-columns: 1fr }` and `.chart-card { padding: 12px }`
- `.table-wrap` scrolling rules
- `.metric-card`, `.metric-value` compact rules
- `.metric-grid-4`, `.metric-grid-3`, `.preview-grid` single-column rules
- `.diag-row > * { flex-basis: 100%% }`
- `.mobile-only { display: block !important; }`
- `.position-cards { display: flex ... }`
- Health findings/score compact rules
- `.rebalancer-section`, `.detailed-metrics-section`, `.price-chart-section` hide rules
- `.fundamentals-grid` 2-col rule
- `.charts-row` research stack rule
- `.q-menu { max-width: 100vw }` research search dropdown
- `.a2hs-banner { ... }` block

- [ ] **Step 3: Verify no syntax errors**

Run: `cd "/Users/joakimhersche/Documents/Python Project/market-dashboard" && python -c "import src.theme; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/theme.py
git commit -m "feat: shared touch tier with pointer:coarse, migrate rules from 767px"
```

---

### Task 3: Add touch-large and touch-small tiers

Add the tablet-specific and phone-specific pointer-based media queries.

**Files:**
- Modify: `src/theme.py` (add new media query blocks after the shared touch tier)

- [ ] **Step 1: Add touch-large tier after the shared `@media (pointer: coarse)` block**

```css
/* ── Touch-large tier (tablets: iPad etc.) ────────────── */
@media (pointer: coarse) and (min-width: 768px) {
  /* Utility classes */
  .touch-large-only { display: block !important; }
  .mobile-only { display: none !important; }

  /* Grids: 2-column layout */
  .kpi-row { grid-template-columns: 1fr 1fr; gap: 10px; }
  .charts-row { grid-template-columns: 1fr 1fr; gap: 12px; }
  .risk-triple { grid-template-columns: 1fr 1fr; gap: 12px; }
  .risk-grid { grid-template-columns: 1fr 1fr; }
  .metric-grid-4 { grid-template-columns: repeat(2, 1fr); }
  .metric-grid-3 { grid-template-columns: repeat(2, 1fr); }
  .preview-grid { grid-template-columns: repeat(2, 1fr); }

  /* Sidebar: partial-width overlay, not full-screen */
  .q-drawer { width: min(320px, 75vw) !important; max-width: min(320px, 75vw) !important; }
  .q-drawer .sidebar {
    padding: 12px 20px !important;
    padding-top: calc(8px + env(safe-area-inset-top, 0px)) !important;
  }

  /* Sidebar bottom actions: sticky */
  .q-drawer .sidebar .sidebar-bottom-actions {
    position: sticky !important;
    bottom: 0 !important;
    background: #161719 !important;
    padding-top: 8px !important;
    margin: 0 -20px !important;
    padding-left: 20px !important;
    padding-right: 20px !important;
    padding-bottom: calc(8px + env(safe-area-inset-bottom, 0px)) !important;
    z-index: 1;
  }
  .q-drawer .sidebar .q-field { margin-bottom: 0 !important; }

  /* Tables: horizontal scroll */
  .table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .table-wrap table { min-width: 600px; }

  /* Diag row: 2-col */
  .diag-row > * { min-width: 0; flex-basis: calc(50%% - var(--grid-gap)); }

  /* Chart card padding */
  .chart-card { padding: 12px !important; }

  /* Health findings: keep row on tablet */

  /* Health score: compact */
  .health-score-container { padding: 14px !important; }
}
```

- [ ] **Step 2: Rename the `@media (max-width: 767px)` block to touch-small tier**

Change the media query from:
```css
@media (max-width: 767px) {
```
To:
```css
/* ── Touch-small tier (phones) ───────────────────────── */
@media (pointer: coarse) and (max-width: 767px) {
```

Also add inside this block:
```css
  /* Utility class */
  .not-phone { display: none !important; }
```

- [ ] **Step 3: Remove the old `@media (max-width: 1023px)` tablet block**

Remove the entire block (lines 348-358):
```css
/* ── Responsive: Tablet (< 1024px) ────────────────────── */
@media (max-width: 1023px) {
  .charts-row { grid-template-columns: 1fr; gap: 12px; }
  ...
}
```

This is superseded by the touch-large tier.

- [ ] **Step 4: Update the KPI medium-width breakpoint**

Keep `@media (max-width: 1100px)` as-is — this still applies to narrow desktop browser windows. No change needed.

- [ ] **Step 5: Verify no syntax errors**

Run: `cd "/Users/joakimhersche/Documents/Python Project/market-dashboard" && python -c "import src.theme; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add src/theme.py
git commit -m "feat: touch-large and touch-small tiers with pointer+width queries"
```

---

### Task 4: Update Python class names — positions (DEFER IF FILE IS DIRTY)

**Pre-check:** Run `git status src/ui/positions.py`. If the file has uncommitted changes from another instance, SKIP this task and note it for later.

**Files:**
- Modify: `src/ui/positions.py:323,334,413`

- [ ] **Step 1: Check file status**

Run: `git status src/ui/positions.py`
If dirty, SKIP this entire task.

- [ ] **Step 2: Change position table from `desktop-only` to `not-phone`**

At line 323, change:
```python
html = f'<div class="desktop-only" style="overflow-x:auto;"><div class="table-wrap"><table>{header}{tbody}</table></div></div>'
```
To:
```python
html = f'<div class="not-phone" style="overflow-x:auto;"><div class="table-wrap"><table>{header}{tbody}</table></div></div>'
```

- [ ] **Step 3: Change the show-individual-purchases toggle from `desktop-only` to `not-phone`**

At line 334, change:
```python
with ui.element("div").classes("desktop-only"):
```
To:
```python
with ui.element("div").classes("not-phone"):
```

- [ ] **Step 4: Change position cards from `mobile-only` to `touch-only`**

At line 413, change:
```python
ui.html(f'<div class="position-cards mobile-only">{cards_html}</div>').classes("w-full")
```
To:
```python
ui.html(f'<div class="position-cards touch-only">{cards_html}</div>').classes("w-full")
```

- [ ] **Step 5: Verify no syntax errors**

Run: `cd "/Users/joakimhersche/Documents/Python Project/market-dashboard" && python -c "from src.ui.positions import build_positions_tab; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add src/ui/positions.py
git commit -m "feat: swap desktop-only/mobile-only to not-phone/touch-only in positions"
```

---

### Task 5: Update Python class names — overview, main, and sidebar

**Files:**
- Modify: `src/ui/overview.py:261,307`
- Modify: `main.py:254,509,524`
- Modify: `src/ui/sidebar.py:504,507,724,746`

- [ ] **Step 1: Overview — change KPI desktop row to `not-phone`**

At line 261, change:
```python
).classes("w-full desktop-only")
```
To:
```python
).classes("w-full not-phone")
```

- [ ] **Step 2: Overview — change KPI mobile card to `touch-only`**

At line 307, change:
```python
</div>''').classes("w-full mobile-only")
```
To:
```python
</div>''').classes("w-full touch-only")
```

Note: The overview KPI experiment starts with cards on all touch devices. If the full desktop KPI row works better on iPad, switch to `desktop-only`/`mobile-only` later.

- [ ] **Step 3: main.py — change sidebar zone-top from `mobile-only` to `touch-only`**

At line 509, change:
```python
with ui.element("div").classes("sidebar-zone-top mobile-only"):
```
To:
```python
with ui.element("div").classes("sidebar-zone-top touch-only"):
```

- [ ] **Step 4: main.py — change sidebar zone-bottom from `mobile-only` to `touch-only`**

At line 524, change:
```python
with ui.element("div").classes("sidebar-zone-bottom mobile-only"):
```
To:
```python
with ui.element("div").classes("sidebar-zone-bottom touch-only"):
```

- [ ] **Step 5: main.py — update swipe hint JS selector**

At line 254, change:
```javascript
var firstSlide = document.querySelector('.mobile-only .q-slide-item .q-slide-item__content');
```
To:
```javascript
var firstSlide = document.querySelector('.touch-only .q-slide-item .q-slide-item__content');
```

- [ ] **Step 6: sidebar.py — change desktop position row to `not-phone`**

At line 504, change:
```python
).classes("w-full desktop-only")
```
To:
```python
).classes("w-full not-phone")
```

- [ ] **Step 7: sidebar.py — change mobile swipe-to-reveal row to `touch-only`**

At line 507, change:
```python
with ui.element("q-slide-item").classes("mobile-only w-full") as slide:
```
To:
```python
with ui.element("q-slide-item").classes("touch-only w-full") as slide:
```

- [ ] **Step 8: sidebar.py — change desktop action buttons to `not-phone`**

At line 724, change:
```python
with ui.column().classes("w-full desktop-only").style("gap:6px;"):
```
To:
```python
with ui.column().classes("w-full not-phone").style("gap:6px;"):
```

- [ ] **Step 9: sidebar.py — change mobile action grid to `touch-only`**

At line 746, change:
```python
with ui.element("div").classes("sidebar-action-grid mobile-only"):
```
To:
```python
with ui.element("div").classes("sidebar-action-grid touch-only"):
```

- [ ] **Step 10: Verify imports work**

Run: `cd "/Users/joakimhersche/Documents/Python Project/market-dashboard" && python -c "from src.ui.overview import build_overview_tab; from src.ui.sidebar import build_sidebar; print('OK')"`
Expected: `OK`

- [ ] **Step 11: Commit**

```bash
git add src/ui/overview.py main.py src/ui/sidebar.py
git commit -m "feat: swap mobile-only/desktop-only to touch-only/not-phone in overview, main, sidebar"
```

---

### Task 6: Move currency pill styles to shared touch tier

The currency pill styles in the phone-only block (`.sidebar-currency-pills`) should also apply on tablets since the sidebar currency section now uses `touch-only`. Move them to the shared touch tier or duplicate for touch-large.

**Files:**
- Modify: `src/theme.py` (touch-small block and shared touch tier)

- [ ] **Step 1: Copy the currency pill CSS to the shared `@media (pointer: coarse)` block**

Add to the shared touch tier:
```css
  /* Currency pills: fill width in sidebar */
  .sidebar-currency-pills {
    display: flex !important;
    width: 100%% !important;
  }
  .sidebar-currency-pills .q-btn {
    flex: 1 !important;
    min-width: 0 !important;
    padding: 8px 4px !important;
    font-size: 13px !important;
  }
```

Then remove the same rules from the touch-small block (they were at lines 475-482 in the original file):
```css
  .sidebar-currency-pills {
    display: flex !important;
    width: 100%% !important;
  }
  .sidebar-currency-pills .q-btn {
    flex: 1 !important;
    min-width: 0 !important;
    padding: 8px 4px !important;
    font-size: 13px !important;
  }
```

- [ ] **Step 2: Verify no syntax errors**

Run: `cd "/Users/joakimhersche/Documents/Python Project/market-dashboard" && python -c "import src.theme; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/theme.py
git commit -m "fix: move currency pill styles to shared touch tier"
```

---

### Task 7: Manual testing in Chrome DevTools

No code changes — verification only.

- [ ] **Step 1: Start the app**

Run: `cd "/Users/joakimhersche/Documents/Python Project/market-dashboard" && python main.py`

- [ ] **Step 2: Test desktop (default)**

Open Chrome, visit the app. Verify:
- Top tab bar visible, bottom tab bar hidden
- No hamburger button
- Multi-column KPI grid
- Desktop controls in header
- Position table visible, position cards hidden

- [ ] **Step 3: Test touch-large (iPad emulation)**

In Chrome DevTools, toggle device toolbar → select iPad Pro. Verify:
- Bottom tab bar visible, top tab bar hidden
- Hamburger button visible, desktop controls hidden
- 2-column grids
- Sidebar opens as partial-width overlay (~320px), not full-screen
- Position cards visible (touch-only), table hidden (not-phone shows table — verify which is active)
- Touch-friendly target sizes

- [ ] **Step 4: Test touch-small (iPhone emulation)**

Select iPhone 12/13/14. Verify:
- Bottom tab bar, hamburger, single-column layout
- Full-width sidebar overlay
- Position cards visible, table hidden
- A2HS banner (if applicable)

- [ ] **Step 5: Document any issues found and create follow-up tasks**
