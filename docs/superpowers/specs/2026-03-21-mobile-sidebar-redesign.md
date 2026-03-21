# Mobile Sidebar Redesign Spec

## Context

The sidebar on mobile is currently a desktop sidebar stretched fullscreen. Position edit/remove buttons are tiny (12-14px icons), the layout wastes vertical space, action buttons get pushed below the fold with many positions, and the currency selector doesn't fill the width. This redesign creates a purpose-built mobile panel.

**Scope:** Mobile only (`@media max-width: 767px`). Desktop sidebar is unchanged.

## Design

### Three-Zone Layout

The mobile sidebar becomes a flex column with three zones:

**Zone 1 — Fixed top:** "Portfolio" title + close button (X, top-right) + search bar. Always visible. The close button replaces the backdrop click as the primary dismiss action (hamburger in header also toggles).

**Zone 2 — Scrollable middle:** Position list. Each row shows: colored dot, ticker, company name + share count, market value. No visible edit/remove icons — actions revealed by swiping left on the row (iOS pattern). The list scrolls independently when positions overflow.

**Zone 3 — Pinned bottom:** Three action buttons (Import, Sample, Clear) in a horizontal grid (3 equal columns, icon above label). Currency pills below, full-width with `flex: 1` per button. This zone is always visible regardless of position count.

### Position Row Design

Each position is a clean row:
```
[dot] AAPL                    $27,467
      Apple Inc. · 15 shares
```

- Colored dot (8px, matches allocation chart)
- Ticker (14px, bold, white)
- Company name + share count (11px, muted, single line)
- Market value (14px, bold, white, right-aligned)
- No visible edit/remove icons

### Swipe-to-Reveal Actions

Swipe a position row left to reveal two action buttons behind it:
- **Edit** — blue background (`#2563EB`), white text + pencil icon
- **Delete** — red background (`#DC2626`), white text + delete icon

Implementation: Use Quasar's `QSlideItem` component via `ui.element('q-slide-item')`. This provides native swipe gesture handling, spring-back animation, and accessibility. Mobile-only — desktop keeps the current inline icon approach.

### First-Time Swipe Hint

On the first sidebar open (per device), auto-peek the first position row 40px to the left, revealing the edge of the Edit button. After 1.5 seconds, animate it back. Store `sidebar_swipe_hint` in localStorage so it only happens once.

### Action Buttons (Bottom Zone)

Three buttons in a horizontal grid replacing the stacked full-width buttons:

```
[ upload    ] [ science   ] [ delete    ]
[ Import    ] [ Sample    ] [ Clear     ]
```

- Monochrome material icons (same style as desktop — `upload`, `science`, `delete_outline`)
- Muted text color (`#94A3B8`), no colored icons
- Border: `1px solid rgba(255,255,255,0.06)`, rounded 8px
- Equal width (`flex: 1`), compact height

### Currency Selector

Full-width pill bar below action buttons. Each currency button uses `flex: 1` so they stretch evenly. Same visual style as the header pills on desktop (active = blue fill, inactive = transparent with muted text).

### CSS Structure

All mobile sidebar styles go inside the existing `@media (max-width: 767px)` block:

- `.q-drawer .sidebar` — flex column, `height: 100%`
- `.sidebar-top-zone` — `flex-shrink: 0`, padding, border-bottom
- `.sidebar-positions-zone` — `flex: 1`, `overflow-y: auto`, `-webkit-overflow-scrolling: touch`
- `.sidebar-bottom-zone` — `flex-shrink: 0`, border-top, background matches sidebar, safe-area bottom padding

### Files to Modify

| File | Changes |
|------|---------|
| `src/theme.py` | Mobile sidebar CSS: three-zone flex layout, position row styles, slide-item overrides, action button grid, currency pills |
| `src/ui/sidebar.py` | Mobile position rows using `q-slide-item`, restructure into zones with CSS classes, action button grid layout |
| `main.py` | Move currency selector into sidebar bottom zone, add swipe hint JS |

### What NOT to Change

- Desktop sidebar layout — completely untouched
- Position data model or edit/remove logic — same callbacks, different UI trigger
- Add position form — same fields, just styled for mobile width
- Existing dialog-based edit/remove confirmations — unchanged
