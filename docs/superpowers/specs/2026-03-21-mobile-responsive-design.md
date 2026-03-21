# Mobile-Responsive Design Spec

## Context

The Market Dashboard is a NiceGUI (Quasar/Vue 3) portfolio tracking app deployed on Fly.io. It already has basic responsive CSS (breakpoints at 767px and 479px, `pointer: coarse` touch targets, PWA manifest with standalone display), but the experience on iPhone and iPad is not purpose-built for mobile use cases.

**Target user**: European cross-border retail investor (10-25 positions, 5-8 sectors, multi-currency) using an affordable dashboard. On mobile, they want a quick status check — not planning or analysis.

**Fly.io constraints**: None relevant. Standard HTTP/WS serving, 1GB RAM, 1 shared CPU. All changes are client-side CSS/layout. NiceGUI's server-rendered model (WebSocket round-trips) is unchanged.

## Design Decisions

### Mobile Tab Bar

**Bottom navigation bar** replacing the current top tab bar on mobile (`max-width: 767px`).

- Fixed to bottom, matching iOS/Android native conventions
- 5 tabs with monochrome SVG stroke icons (20x20, stroke-width 1.8)
- Active tab: accent blue (`#3B82F6`) icon + label; inactive: muted gray (`#64748B`)
- Labels below icons, 9px font
- Bottom padding accounts for iOS safe area (home indicator)
- Current top tab bar hidden on mobile via CSS `display: none`
- Desktop remains unchanged

**Icons** (all stroke-only, no fill):
- Overview: 4-square grid
- Positions: horizontal lines with dots (list)
- Health: heartbeat/pulse line
- Research: magnifying glass
- Guide: book

### Tab Visibility on Mobile

| Tab | Mobile | Rationale |
|-----|--------|-----------|
| Overview | Visible | Landing page, primary glance |
| Positions | Visible | "How are my holdings?" |
| Health | Visible (lite) | Score + findings + sectors + news |
| Research | Visible | Social use case — show a friend |
| Guide | Visible | Reference docs on the go |
| Forecast | **Hidden** | Monte Carlo controls unusable on phone, chart needs width |
| Income | **Hidden** | Quarterly planning, not glance-and-go |

Hide entire Forecast and Income tabs on mobile by not rendering them in the tab bar and hiding their panels.

### Overview Tab (Mobile)

**Consolidated hero card** instead of 5 separate KPI cards:

- Single card containing:
  - Portfolio value (28px, hero treatment) with decimal in muted color
  - Today's change: amount + percentage badge + "today" label
  - Horizontal divider
  - Bottom row: Total Return (left) and Positions count (right)
- Below the card: subtle inline text row showing Contributed and Health Score
- Charts stack vertically: Allocation → Comparison → Contributions
- Allocation chart: full-width horizontal bars (same Plotly chart, just single column)
- Comparison chart: full-width with range toggles (3M/6M/1Y/Max pills)
- Contributions chart: full-width below

**Desktop unchanged.**

### Positions Tab (Mobile)

**Card-based layout** replacing the 13-column HTML table:

- Sort toggle row at top: position count label + sort pills (Weight / Return / Day)
- Each position rendered as a card:
  - Top row: colored dot + ticker + company name (left), value + return % (right)
  - Bottom row (subtle divider): shares count + weight % (left), daily P&L (right)
- Cards stacked vertically with 6px gap
- Color coding: green for positive return/daily, red for negative
- Colored dots match the portfolio color map (same as allocation chart)
- All positions shown (no pagination — scroll is fine for 15-20 cards)

**Desktop unchanged** — keeps the full HTML table.

### Health Tab (Mobile Lite)

**Sections shown on mobile:**

1. **Health Score** — compact inline layout (not centered circle):
   - 64px score circle (border colored by score: green/amber/red) + summary text beside it
   - No expandable "how is this calculated" section on mobile
2. **Key Findings** — stacked vertically (not horizontal flex row):
   - Same card design: left color border + background tint + headline + body
   - Full width per card, 6px gap between
3. **Sector Exposure** — simplified to sector-level bars only:
   - No nested ticker rows within sectors
   - Each sector: name + colored bar + percentage
4. **News** — compact headline list:
   - Ticker badge + publisher + time on first line
   - Headline on second line
   - Dividers between items

**Sections hidden on mobile:**
- Rebalancing Calculator (entire section) — planning tool, needs desktop
- Detailed Metrics expansion (analytics table + correlation heatmap) — too data-dense

**Desktop unchanged.**

### Research Tab (Mobile)

- Search bar prominent at top with recent search tags below
- Company header card: name + sector info (left), price + daily change (right)
- Fundamentals grid: 3 columns → **2 columns** on mobile
- Portfolio Fit: condensed to score change visualization (current → projected with delta badge) + one-line impact summary. No bullet list.
- Peer Comparison table: kept with horizontal scroll (`-webkit-overflow-scrolling: touch`)
- **Price History chart hidden on mobile** — Plotly charts are heavy on small screens and the key data is already in the fundamentals cards
- News section below peers (same compact format as Health tab news)

**Desktop unchanged.**

### Guide Tab

No structural changes. Tighter padding on mobile (already handled by existing CSS breakpoints). Pure text content renders well on any width.

### Sidebar on Mobile

The sidebar (portfolio management: add/edit/remove positions) is already hidden on mobile behind a hamburger menu overlay. **No changes needed.** Users manage their portfolio on desktop; mobile is read-only status checking.

## Implementation Strategy

All changes are **CSS-only where possible**, using existing `@media (max-width: 767px)` breakpoints. Where the desktop and mobile layouts are structurally different (positions cards vs table, overview hero card vs KPI grid), use CSS `display: none` / `display: block` to show/hide the appropriate version.

### Bottom Tab Bar (requires Python + JS, not CSS-only)

The bottom tab bar is a new `ui.html` element rendered in `main.py`, hidden on desktop via CSS. **Tab switching requires JavaScript bridging**: clicking a bottom tab button must programmatically trigger the hidden top `ui.tabs` widget, since `ui.tab_panels` is reactively bound to it. Implementation: each bottom tab button calls `ui.run_javascript()` to click the corresponding hidden top tab element, preserving the existing panel-switching logic. The top tab bar gets `display: none` on mobile.

**URL-based tab restoration**: `main.py` reads `?tab=Forecast` from query params. On mobile, if the requested tab is Forecast or Income (hidden tabs), redirect to Overview instead.

**Tab label**: The bottom bar uses "Health" (not "Portfolio Health") to fit the 9px label width. The mapping from bottom bar label to internal tab name must account for this.

### Overview Hero Card

The existing KPI grid uses **inline** `grid-template-columns: 1fr 1fr 1fr 1fr 1fr` style (in `overview.py`), which beats CSS class overrides. Solution: render both layouts — the existing KPI grid wrapped in `.desktop-only`, and the new hero card wrapped in `.mobile-only`. The inline style stays on the desktop version; the mobile version is independent HTML.

### Positions Cards

Render both the table (desktop) and the card list (mobile) in `positions.py`, hide one per breakpoint. The card renderer is a separate function that takes the same data. **Multi-lot toggle**: hidden on mobile — cards always show the aggregated view per ticker (no individual purchase expansion). This avoids duplicating the toggle logic.

### Hidden Tabs (Forecast, Income)

Hide via CSS on mobile. They stay in the DOM but are invisible and inaccessible (no tab bar button, panel hidden).

### Hidden Sections (rebalancer, detailed metrics, price chart)

Wrap in a container element with a CSS class that hides on mobile. These wrapper elements need to be added — they don't exist yet. Specifically:
- `_render_rebalancing_calculator` in `health.py`: wrap outer `ui.column` with `.rebalancer-section`
- Detailed metrics expansion in `health.py`: wrap with `.detailed-metrics-section`
- Price chart in `research.py`: wrap with `.price-chart-section`
- Fundamentals grid in `research.py`: add `.fundamentals-grid` class for column override

### Plotly Charts on Mobile

For charts that remain visible on mobile (Allocation, Comparison, Contributions on Overview; Sector chart on Health), configure Plotly with `displayModeBar: false` on mobile. The modebar buttons are unusable on touch screens and the comparison chart already has its own toggle controls. This can be done via the existing `config` dict passed to Plotly figure rendering.

### New CSS Classes Needed

```css
/* Bottom tab bar */
.mobile-tab-bar { display: none; }
@media (max-width: 767px) {
  .mobile-tab-bar { display: flex; position: fixed; bottom: 0; /* ... */ }
  .q-tabs { display: none; }  /* hide top tabs */
  body { padding-bottom: 64px; }  /* space for bottom bar */
}

/* Mobile-only / desktop-only visibility */
.mobile-only { display: none; }
.desktop-only { display: block; }
@media (max-width: 767px) {
  .mobile-only { display: block; }
  .desktop-only { display: none; }
}

/* Positions card list */
.position-cards { display: none; }
@media (max-width: 767px) {
  .position-cards { display: flex; flex-direction: column; gap: 6px; }
  .table-wrap { display: none; }
}

/* Health mobile simplifications */
@media (max-width: 767px) {
  .rebalancer-section { display: none; }
  .detailed-metrics-section { display: none; }
}

/* Research mobile */
@media (max-width: 767px) {
  .fundamentals-grid { grid-template-columns: 1fr 1fr; }
  .price-chart-section { display: none; }
}
```

### Files to Modify

| File | Changes |
|------|---------|
| `src/theme.py` | Add mobile CSS classes (bottom tab bar, mobile-only/desktop-only, position cards, hide classes) |
| `main.py` | Render bottom tab bar element (hidden on desktop), add mobile-only class to hidden tab panels |
| `src/ui/overview.py` | Add mobile hero card layout (hidden on desktop), wrap KPI grid in desktop-only |
| `src/ui/positions.py` | Add card-based position renderer (hidden on desktop), wrap table in desktop-only |
| `src/ui/health.py` | Wrap rebalancer in hideable container, wrap detailed metrics in hideable container, add mobile class to sector breakdown for simplified rendering |
| `src/ui/research.py` | Add mobile class to fundamentals grid, wrap price chart in hideable container, add mobile class to portfolio fit for condensed version |

### What NOT to Change

- Desktop layout — completely untouched
- Data fetching / portfolio logic — no changes
- Sidebar — already handles mobile
- Guide tab — already works
- PWA manifest — already configured
- Fly.io deployment — no changes needed
