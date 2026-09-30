# LEAP UI Design System Inventory

This document serves as the official catalog and visual baseline for the visual design system of the AI-Powered KPI Extractor & Interactive Bluebook Generator (LEAP).

---

## Component Catalog

### 1. Dashboard KPI Cards
* **Canonical Selector**: `.blueprint-header-stats .leap-metric-card`
* **Pages Using It**: `index.html` (Index Dashboard)
* **Purpose**: Summarizes the overall KPI count, confidence, and validated metric counts at the top of the dashboard.
* **Design Tokens Used**: `var(--surface)`, `var(--platinum-border)`, `var(--text-muted)`, `var(--charcoal)`
* **Typography Scale**: Value: `font-size: 40px`, Label: `font-size: 10px` (uppercase, bold)
* **Spacing System**: `gap: 8px` between content, `padding: 24px` on all sides
* **Radius**: `8px`
* **Background Token**: `var(--surface)` (solid white in light mode)
* **Border Token**: `1px solid color-mix(in srgb, var(--platinum-border) 60%, transparent)`
* **Shadow Token**: `none`
* **Dark Mode Behavior**: Background shifts to `#111923` or inherits transparent panels where scoped.
* **Allowed to Inherit**: Discovery metric cards.
* **Prohibited from Inheriting**: Executive dashboard metrics, dossier right-rail cards.

### 2. Portfolio Command Card
* **Canonical Selector**: `.dashboard-executive-panel-primary`
* **Pages Using It**: `index.html` (Index Dashboard)
* **Purpose**: Highlight panel displaying overall Operational KPI coverage statistics.
* **Design Tokens Used**: `var(--surface)`, `var(--business-teal)`, `var(--surface-soft)`
* **Typography Scale**: Title: `font-size: 24px`, Metric Value: `font-weight: 700; font-size: clamp(44px, 4vw, 68px)`
* **Spacing System**: `padding: 30px` on all sides
* **Radius**: `14px`
* **Background Token**: `linear-gradient(135deg, color-mix(in srgb, var(--surface) 92%, var(--business-teal)) 0%, var(--surface) 58%, color-mix(in srgb, var(--surface-soft) 80%, var(--surface)) 100%)`
* **Border Token**: `none`
* **Shadow Token**: `0 18px 46px rgba(15, 23, 42, 0.07)`
* **Dark Mode Behavior**: Shifts to `linear-gradient(135deg, #111923 0%, #0f151d 60%, #0b121a 100%)`
* **Allowed to Inherit**: None.
* **Prohibited from Inheriting**: Definition Authority cards, right-rail cards.

### 3. Definition Authority Panel
* **Canonical Selector**: `.dashboard-executive-panel`
* **Pages Using It**: `index.html` (Index Dashboard)
* **Purpose**: Secondary summary container displaying governance and definition readiness indicators.
* **Design Tokens Used**: `var(--surface)`, `var(--surface-soft)`
* **Typography Scale**: Title: `font-size: 20px`, Subheading: `font-size: 13px`
* **Spacing System**: `padding: 24px` on all sides
* **Radius**: `14px`
* **Background Token**: `color-mix(in srgb, var(--surface) 82%, var(--surface-soft))`
* **Border Token**: `none`
* **Shadow Token**: `0 10px 28px rgba(15, 23, 42, 0.045)`
* **Dark Mode Behavior**: Background changes to `#0f151d`
* **Allowed to Inherit**: None.
* **Prohibited from Inheriting**: Primary Portfolio Command cards.

### 4. Discovery Intelligence Band
* **Canonical Selector**: `.discovery-intelligence-band`
* **Pages Using It**: `discovery_report.html` (Discovery Workspace)
* **Purpose**: Large highlighted group container presenting portfolio metrics and confidence classifications.
* **Design Tokens Used**: `var(--surface-soft)`, `var(--charcoal)`, `var(--platinum-border)`
* **Typography Scale**: Heading: `font-size: 18px`, Paragraph: `font-size: 13px`
* **Spacing System**: `gap: 16px` inner cells, `padding: 20px`
* **Radius**: `12px`
* **Background Token**: `var(--surface-soft)` (light grey)
* **Border Token**: `1px solid var(--platinum-border)`
* **Shadow Token**: `none`
* **Dark Mode Behavior**: Shifts to `#0b121a`
* **Allowed to Inherit**: None.
* **Prohibited from Inheriting**: Right rail cards.

### 5. Discovery Metric Cards
* **Canonical Selector**: `.metric-indicator-block`
* **Pages Using It**: `discovery_report.html` (Discovery Workspace)
* **Purpose**: General statistical number block displaying counts and percentages.
* **Design Tokens Used**: `var(--surface)`, `var(--platinum-border)`
* **Typography Scale**: Value: `font-size: 40px`, Label: `font-size: 10px`
* **Spacing System**: `padding: 24px`
* **Radius**: `8px`
* **Background Token**: `var(--surface)`
* **Border Token**: `1px solid var(--platinum-border)`
* **Shadow Token**: `none`
* **Dark Mode Behavior**: Transparent overlays inside intelligence bands, solid backgrounds elsewhere.
* **Allowed to Inherit**: Dashboard KPI cards.
* **Prohibited from Inheriting**: Dossier hero cards.

### 6. RACI Risk Cards
* **Canonical Selector**: `.raci-risk-card.is-primary`
* **Pages Using It**: `raci_directory.html` (RACI Directory)
* **Purpose**: Solid card block representing ownership concentration levels.
* **Design Tokens Used**: `var(--charcoal)`, `var(--surface)`
* **Typography Scale**: Title Value: `font-size: 20px`, Label: `font-size: 10px`
* **Spacing System**: `gap: 8px`, `padding: 16px`
* **Radius**: `12px`
* **Background Token**: `color-mix(in srgb, var(--charcoal) 90%, var(--surface))`
* **Border Token**: `none`
* **Shadow Token**: `none`
* **Dark Mode Behavior**: Background shifts to `color-mix(in srgb, var(--charcoal) 72%, var(--surface))`
* **Allowed to Inherit**: None (serves as canonical reference).
* **Prohibited from Inheriting**: All standard metric cards.

### 7. KPI Dossier Hero Cards
* **Canonical Selector**: `.kpi-dossier-workspace .kpi-hero-metrics .kpi-hero-metric`
* **Pages Using It**: KPI Dossiers
* **Purpose**: Horizontal metadata block headers presenting status, owner, domain, and validation values.
* **Design Tokens Used**: `var(--charcoal)`, `var(--surface)`
* **Typography Scale**: Value: `font-size: 16px`, Label: `font-size: 10px`
* **Spacing System**: `gap: 4px`, `padding: 16px`
* **Radius**: `12px`
* **Background Token**: `color-mix(in srgb, var(--charcoal) 90%, var(--surface))`
* **Border Token**: `none`
* **Shadow Token**: `none`
* **Dark Mode Behavior**: Background shifts to `color-mix(in srgb, var(--charcoal) 72%, var(--surface))`
* **Allowed to Inherit**: Copies visual tokens from RACI risk cards.
* **Prohibited from Inheriting**: Base metric card backgrounds.

### 8. KPI Dossier Right Rail Cards
* **Canonical Selector**: `.kpi-dossier-workspace .kpi-dossier-right .sidebar-card`
* **Pages Using It**: KPI Dossier Pages
* **Purpose**: Meta property details, action links, and system indicators.
* **Design Tokens Used**: `var(--surface)`, `var(--platinum-border)`
* **Typography Scale**: Title: `font-size: 12px` (uppercase), Copy: `font-size: 12.5px`
* **Spacing System**: `margin-bottom: 18px`, `padding: 20px 22px 20px 24px`
* **Radius**: `10px`
* **Background Token**: `var(--surface)`
* **Border Token**: `1px solid var(--platinum-border)`
* **Shadow Token**: `none`
* **Dark Mode Behavior**: Border color shifts to `rgba(255, 255, 255, 0.08)`
* **Allowed to Inherit**: Action cards, metadata cards.
* **Prohibited from Inheriting**: Dashboard executive panels.

### 9. Provenance Rows
* **Canonical Selector**: `.evidence-tab-panel[data-evidence-panel="provenance"] .evidence-detail-grid > div`
* **Pages Using It**: KPI Dossier Pages (Provenance Tab)
* **Purpose**: Double-column tabular grid row containing source metadata and location variables.
* **Design Tokens Used**: `var(--surface)`
* **Typography Scale**: Label: `font-size: 11px`, Value: `font-size: 13px`
* **Spacing System**: `gap: 24px` (flex-gap), label width fixed at `220px`
* **Radius**: `8px`
* **Background Token**: `var(--surface)`
* **Border Token**: `none`
* **Shadow Token**: `none`
* **Dark Mode Behavior**: Inherits standard active tab panel text transforms and colors.
* **Allowed to Inherit**: None.
* **Prohibited from Inheriting**: Code lineages, inputs panel elements.

### 10. Disclosure Controls
* **Canonical Selector**: `.evidence-lineage-panel > summary::before` / `.terminal-toggle-btn`
* **Pages Using It**: All pages (collapsible blocks and compilation cockpit console)
* **Purpose**: Simple visual text marker (`+` / `−`) that signals and triggers block expansion.
* **Design Tokens Used**: `var(--business-teal)`
* **Typography Scale**: Symbol: `font-size: 13px` (JetBrains Mono font family)
* **Spacing System**: `width: 18px` width allocation, `margin-left: 8px`
* **Radius**: `none`
* **Background Token**: `transparent`
* **Border Token**: `none`
* **Shadow Token**: `none`
* **Dark Mode Behavior**: Retains monospace visual weights and opacity triggers.
* **Allowed to Inherit**: Terminal toggle buttons.
* **Prohibited from Inheriting**: Toggle perspective selectors.
