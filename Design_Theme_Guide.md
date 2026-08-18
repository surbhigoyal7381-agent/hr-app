# GRACE GROUP HRMS - ENTERPRISE DESIGN THEME GUIDE
## Professional, Human-Centric Design System Inspired by Industry-Leading HRMS Platforms

---

## EXECUTIVE OVERVIEW

This design theme guide creates a **modern, approachable, enterprise-grade** interface for the Demo Group HRMS application. The design philosophy centers on:

- **Human-Centric Design:** Employee photos, warm colors, approachable interactions
- **Enterprise Professionalism:** Purple as primary color, clean typography, clear hierarchy
- **Clarity & Usability:** Generous whitespace, card-based layouts, intuitive navigation
- **Trust & Reliability:** Consistent patterns, accessible colors, professional imagery

**Target Audience:** 200 employees ranging from delivery personnel to management at Demo Group Logistics/FMCG company.

---

## 1. COLOR PALETTE

### Primary Color Scheme

| Color | Hex Value | Usage | Notes |
|---|---|---|---|
| **Primary Purple** | #5B4B8A | Buttons, headers, primary actions, links | Deep, professional, trustworthy |
| **Purple Hover** | #6E5FA0 | Interactive hover states | Slightly lighter for interaction feedback |
| **Purple Light** | #E8E5F2 | Backgrounds, subtle highlights | Very light tint for backgrounds |
| **Purple Dark** | #3D3461 | Text on light backgrounds, emphasis | Dark, high contrast |

### Secondary & Accent Colors

| Color | Hex Value | Usage | Notes |
|---|---|---|---|
| **Soft Rose/Pink** | #FFB4D1 | Status badges (overdue, alert), accents | Warm, attention-grabbing but soft |
| **Teal/Turquoise** | #6DB5B8 | Success states, positive actions, highlights | Fresh, approachable, indicates completion |
| **Warm Cream** | #F8F6F3 | Main background color | Off-white with warm undertone, easy on eyes |
| **Light Gray** | #F3F1ED | Card backgrounds, secondary surfaces | Subtle, creates depth without harshness |

### Semantic Colors

| State | Color | Hex | Usage |
|---|---|---|---|
| Success / Complete | Teal | #6DB5B8 | Checkmarks, done status, positive actions |
| Warning / Overdue | Soft Pink | #FFB4D1 | Overdue badges, time-sensitive alerts |
| Alert / Critical | Coral Red | #E85D75 | Critical alerts, denials, blockers |
| Pending / In Progress | Light Purple | #C4B5E0 | Pending status, workflows in progress |
| Disabled / Inactive | Light Gray | #D8D5CE | Disabled buttons, inactive states |

### Data Visualization Colors

For charts, graphs, and analytics:

| Element | Colors | Usage |
|---|---|---|
| **Chart Palette 1** | #E05B9A (Magenta), #F5D547 (Yellow), #4A90E2 (Blue), #6DB5B8 (Teal) | Pie charts, bar charts, comparison visualizations |
| **Chart Palette 2** | #FF6B6B (Red), #4ECDC4 (Teal), #45B7D1 (Light Blue), #96CEB4 (Green) | Line charts, trend analysis |
| **Neutral Gray** | #8B8680 | Labels, supporting text in charts |

### Text Colors

| Usage | Color | Hex | Contrast Ratio |
|---|---|---|---|
| Primary Text (Headings) | Dark Charcoal | #2D2622 | 12:1 (AAA) |
| Secondary Text (Body) | Medium Gray | #5C5854 | 7:1 (AA) |
| Tertiary Text (Labels, hints) | Light Gray | #8B8680 | 4.5:1 (AA) |
| Link Text | Primary Purple | #5B4B8A | 5.5:1 (AA) |

### Background Hierarchy

| Layer | Color | Hex | Usage |
|---|---|---|---|
| Page Background | Warm Cream | #F8F6F3 | Main canvas |
| Card/Container | White | #FFFFFF | Elevated surfaces, cards, modals |
| Secondary Container | Light Gray | #F3F1ED | Sections, grouped content |
| Accent Background | Purple Light | #E8E5F2 | Highlights, active states |

---

## 2. TYPOGRAPHY SYSTEM

### Font Family

```
Primary Font Stack: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif

Alternative: "Inter", "Poppins", or "Open Sans" (similar modern sans-serif)
```

**Rationale:** Clean, modern, highly readable on all devices. Similar to industry-leading HRMS platforms.

### Type Scale

| Type | Size | Weight | Line Height | Usage | Example |
|---|---|---|---|---|---|
| **H1 - Page Title** | 32px | 700 (Bold) | 40px | Main page headings | "My Employees" |
| **H2 - Section Header** | 24px | 600 (SemiBold) | 32px | Major sections | "Continuous Performance" |
| **H3 - Card Title** | 18px | 600 (SemiBold) | 26px | Card titles | "Salary review" |
| **H4 - Subsection** | 16px | 600 (SemiBold) | 24px | Small headings | "Personal data" |
| **Body - Regular** | 14px | 400 (Regular) | 22px | Main body text, descriptions | Employee names, task descriptions |
| **Body - Emphasized** | 14px | 500 (Medium) | 22px | Important body text | Selected states, emphasis |
| **Label** | 12px | 500 (Medium) | 18px | Form labels, badges | "Due today", employee ID |
| **Small Text** | 12px | 400 (Regular) | 18px | Helper text, dates | "Ready for meeting" |
| **Tiny** | 11px | 400 (Regular) | 16px | Captions, metadata | "14 days overdue" |

### Font Weight Usage

| Weight | Value | Usage |
|---|---|---|
| Bold | 700 | Page titles, primary headings |
| SemiBold | 600 | Section headers, card titles |
| Medium | 500 | Labels, form text, navigation |
| Regular | 400 | Body text, descriptions |

### Text Hierarchy Example

```
H1: "My employees" (32px, Bold, #2D2622)
  ↓ Main heading - most prominent

H3: "Continuous Performance" (18px, SemiBold, #2D2622)
  ↓ Section header - secondary heading

Body: "1:1 -samtale (Sales Norway)" (14px, Regular, #5C5854)
  ↓ Main body text - supporting information

Label: "Ready for meeting" (12px, Regular, #8B8680)
  ↓ Tertiary information - smallest, lowest contrast
```

---

## 3. SPACING & GRID SYSTEM

### Base Unit

**Base spacing unit: 8px**

All spacing follows multiples of 8px for consistent, scalable layouts.

### Spacing Scale

| Spacing | Value | Usage |
|---|---|---|
| xs | 4px | Micro-spacing (icon padding, tight components) |
| sm | 8px | Small gaps (element padding, tight sections) |
| md | 16px | Medium gaps (section spacing, card padding) |
| lg | 24px | Large gaps (major sections, cards) |
| xl | 32px | Extra large gaps (section breaks) |
| 2xl | 48px | Page-level spacing |
| 3xl | 64px | Major sections |

### Grid System

- **12-column responsive grid**
- **Desktop (1200px+):** Full 12 columns
- **Tablet (768-1199px):** 8-column adaptive
- **Mobile (< 768px):** 4-column stacked

### Card & Container Spacing

```
Card Padding: 24px (md) top/bottom, 20px (sm+md) left/right
Card Margin: 16px (md) between cards
Section Gap: 32px (lg) between major sections
```

### Example Layout: Dashboard Card

```
┌─────────────────────────────────────────┐
│  24px padding top                       │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │ "Salary review"                  │ 20px
│  │ (Card Title, 18px, SemiBold)     │ lr pad
│  └──────────────────────────────────┘   │
│                                         │
│  16px gap                              │
│                                         │
│  📋 "Awaiting release confirmation"   │
│  (Body text, 14px)                    │
│                                         │
│  16px gap                              │
│                                         │
│  [Badge: "14 days overdue"]            │
│                                         │
│  24px padding bottom                    │
└─────────────────────────────────────────┘
```

---

## 4. COMPONENT LIBRARY

### 4.1 Buttons

#### Primary Button (Call-to-Action)

```
Appearance:
├─ Background: #5B4B8A (Primary Purple)
├─ Text: White (#FFFFFF)
├─ Padding: 12px 24px
├─ Border Radius: 6px
├─ Font: 14px, Medium (500)
├─ Box Shadow: 0 2px 8px rgba(91, 75, 138, 0.2)

States:
├─ Default: #5B4B8A
├─ Hover: #6E5FA0 (lighter purple) + shadow increase
├─ Active: #3D3461 (darker purple)
├─ Disabled: #D8D5CE (light gray) with 50% opacity

Usage: "Create new", "Save", "Submit", "Start new", "Finish"
```

#### Secondary Button

```
Appearance:
├─ Background: #F3F1ED (Light gray)
├─ Text: #5B4B8A (Purple)
├─ Border: 1px solid #D8D5CE
├─ Padding: 12px 24px
├─ Border Radius: 6px

Usage: "View all", "Cancel", "Edit", "Send reminders"
```

#### Ghost Button (Minimal)

```
Appearance:
├─ Background: Transparent
├─ Text: #5B4B8A (Purple)
├─ Border: None
├─ Underline on hover

Usage: Links, secondary actions, "View audit trail"
```

### 4.2 Cards

#### Task Card

```
┌─────────────────────────────────────────┐
│ 20px                                    │
│  ╔════════════════════════════════╗     │
│  ║ Salary review                  ║     │
│  ║ (H3, SemiBold)                 ║ 20px
│  ║                                ║ pad
│  ║ Awaiting release confirmation  ║
│  ║ (Body, Regular)                ║
│  ║                                ║
│  ║ [Badge: 14 days overdue]       ║
│  ╚════════════════════════════════╝     │
│ 20px                                    │
└─────────────────────────────────────────┘

Card Styling:
├─ Background: White (#FFFFFF)
├─ Border: 1px solid #E8E5F2 (light purple border)
├─ Border Radius: 8px
├─ Box Shadow: 0 2px 6px rgba(0, 0, 0, 0.05)
├─ Padding: 20px
├─ Transition: 0.2s ease (for hover effects)

Hover State:
├─ Shadow: 0 4px 12px rgba(0, 0, 0, 0.1)
├─ Border Color: #D8D5CE
```

#### Employee Avatar Card

```
┌──────────────┐
│              │
│   [Avatar]   │  Avatar: 40px-64px circle
│              │  Image: Employee photo
│              │  Background: #E8E5F2 if no image
│  John Smith  │
│  Manager     │
│              │
└──────────────┘

Styling:
├─ Avatar Size: 48px-64px
├─ Border Radius: 50% (perfect circle)
├─ Border: 2px solid white
├─ Box Shadow: 0 2px 4px rgba(0, 0, 0, 0.1)
├─ Name: 14px SemiBold
├─ Role: 12px Regular, light gray
```

### 4.3 Badges & Status Indicators

#### Status Badge - Overdue

```
Text: "14 days overdue"
├─ Background: #FFB4D1 (Soft pink)
├─ Text Color: #C41E3A (Dark red)
├─ Padding: 6px 12px
├─ Border Radius: 20px
├─ Font: 12px, Medium
```

#### Status Badge - In Progress

```
Text: "Ready for meeting"
├─ Background: #E8E5F2 (Light purple)
├─ Text Color: #5B4B8A (Purple)
├─ Padding: 6px 12px
├─ Border Radius: 20px
├─ Font: 12px, Medium
```

#### Status Badge - Completed

```
Text: "Done" with ✓ icon
├─ Background: #D4F1D4 (Light green)
├─ Text Color: #2D6E2D (Dark green)
├─ Padding: 6px 12px
├─ Border Radius: 20px
├─ Font: 12px, Medium
├─ Icon: ✓ (2px left margin)
```

### 4.4 Forms & Input Fields

#### Text Input / Text Area

```
┌─────────────────────────────────┐
│ Label: "Last name" *            │ 12px, Medium, #2D2622
│                                 │ 8px gap
│ ┌───────────────────────────────┤
│ │ Leder                          │ 14px, Regular text
│ └───────────────────────────────┤ 
│                                 │
│ Optional: "✎ Edit" link         │ Light purple link
└─────────────────────────────────┘

Input Styling:
├─ Background: White (#FFFFFF)
├─ Border: 1px solid #D8D5CE
├─ Border Radius: 4px
├─ Padding: 10px 12px
├─ Font: 14px, Regular
├─ Placeholder: #8B8680 (light gray)

Focus State:
├─ Border Color: #5B4B8A (purple)
├─ Box Shadow: 0 0 0 3px rgba(91, 75, 138, 0.1)
├─ Outline: None
```

#### Checkbox / Toggle

```
Unchecked: ☐ "View employees"
├─ Border: 2px solid #D8D5CE
├─ Size: 16px × 16px
├─ Border Radius: 3px

Checked: ☑ "View employees"
├─ Background: #5B4B8A (Purple)
├─ Check: White ✓
├─ Border Radius: 3px

Label:
├─ Font: 14px, Regular
├─ Color: #2D2622
├─ Margin Left: 8px
```

### 4.5 Navigation & Sidebar

#### Sidebar Menu Item

```
Default State:
┌──────────────────────┐
│ Personal data        │  
│ (14px, Regular)      │
└──────────────────────┘
├─ Padding: 12px 16px
├─ Background: Transparent
├─ Text Color: #2D2622

Active/Selected State:
┌──────────────────────┐ ← Background: #E8E5F2
│ Personal data        │  
│ (14px, Regular)      │
└──────────────────────┘
├─ Background: #E8E5F2 (Light purple)
├─ Text Color: #5B4B8A (Purple, bold)
├─ Border Left: 3px solid #5B4B8A

Hover State:
├─ Background: #F3F1ED (Very light gray)
├─ Transition: 0.15s ease
```

#### Top Navigation / Header

```
┌─────────────────────────────────────────────────────────────┐
│ [☰ Menu] "My tasks" [15]     [⚙] [🔔] [👤]                │
│ Background: White (#FFFFFF)                                │
│ Border Bottom: 1px solid #E8E5F2                           │
│ Padding: 16px 24px                                         │
│ Height: 64px                                               │
└─────────────────────────────────────────────────────────────┘

Styling:
├─ Background: White
├─ Border Bottom: 1px solid #E8E5F2
├─ Title: 18px SemiBold, #2D2622
├─ Icons: 24px, #5B4B8A (hover: darker)
├─ Badge Count: 12px SemiBold, White text on #FFB4D1
```

---

## 5. ELEVATION & SHADOWS

### Shadow System

Shadows create depth and hierarchy in the interface.

```
Elevation 1 (Cards at rest):
Box Shadow: 0 2px 6px rgba(0, 0, 0, 0.05)
(Subtle, minimal depth)

Elevation 2 (Cards on hover):
Box Shadow: 0 4px 12px rgba(0, 0, 0, 0.1)
(Moderate depth, interactive)

Elevation 3 (Modals, dropdowns):
Box Shadow: 0 8px 24px rgba(0, 0, 0, 0.15)
(Strong depth, overlaid elements)

Elevation 4 (Pop-ups, notifications):
Box Shadow: 0 12px 32px rgba(0, 0, 0, 0.2)
(Maximum depth, alerts requiring attention)
```

### Border Radius

| Element | Radius | Usage |
|---|---|---|
| **Buttons** | 6px | Friendly, modern appearance |
| **Cards** | 8px | Slightly rounded, approachable |
| **Input Fields** | 4px | Subtle, not overdone |
| **Avatars** | 50% | Perfect circles for faces |
| **Badges** | 20px | Pill-shaped, rounded |
| **Modals** | 12px | Large, prominent overlays |

---

## 6. ICONS & IMAGERY

### Icon Style

- **Style:** Clean, line-based icons (2px stroke weight)
- **Size:** 20px × 20px (small), 24px × 24px (standard), 32px × 32px (large)
- **Color:** 
  - Default: #5B4B8A (Purple)
  - Success: #6DB5B8 (Teal)
  - Alert: #FFB4D1 (Pink)
- **Stroke:** Solid, rounded line endings

### Common Icons

```
📋 Tasks/Work
👥 Employees/People
📊 Analytics/Reports
⚙️ Settings/Configuration
🎯 Goals/Objectives
✓ Complete/Done
📍 Status indicator
🔔 Notifications
👤 Profile/User
📅 Calendar/Date
```

### Imagery & Photography

#### Employee Avatars

- **Size:** 40px-64px circles
- **Style:** Professional headshots (recommended size: 200px × 200px PNG)
- **Fallback:** If no image, use colored background (#E8E5F2) with initials (18px, SemiBold, #5B4B8A)
- **Border:** 2px white border on avatars

#### Illustration Style

- **Context:** Onboarding flows, welcome screens, empty states
- **Style:** Friendly, illustrative (cartoon/character style)
- **Color Palette:** Use primary color scheme (purples, teals, pinks)
- **Examples:** Two people having a conversation (Performance Dialogue), employee working (onboarding), charts (analytics)

### Accent Illustrations

For empty states and welcome messages:
- Warm, human-centric illustrations
- Show real people in professional scenarios
- Use consistent character style across the application
- Dimensions: 200px-300px width for card layouts

---

## 7. LAYOUT PATTERNS

### Dashboard Layout

```
┌─────────────────────────────────────────────────┐
│ Header: "My Dashboard"                          │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────┐  ┌──────────────────┐   │
│  │                  │  │                  │   │
│  │ My tasks (15)    │  │ Shortcuts (18)   │   │
│  │ ────────────     │  │ ────────────     │   │
│  │ Salary review    │  │ [Icon] [Icon]    │   │
│  │ Lennsjustering   │  │ [Icon] [Icon]    │   │
│  │ [Badge: 14d]     │  │                  │   │
│  │                  │  │                  │   │
│  └──────────────────┘  └──────────────────┘   │
│                                                 │
│  ┌──────────────────┐  ┌──────────────────┐   │
│  │ My employees (9) │  │ Appraisals (2)   │   │
│  │ ────────────     │  │ ────────────     │   │
│  │ [Avatar] [Avatar]│  │ [Chart]          │   │
│  │ [Avatar] [Avatar]│  │ Competency       │   │
│  │ [Avatar] [Avatar]│  │ Due: 31.12.26    │   │
│  │                  │  │                  │   │
│  └──────────────────┘  └──────────────────┘   │
│                                                 │
└─────────────────────────────────────────────────┘

Grid: 2 columns on desktop, 1 on mobile
Card Gap: 16px (md)
Section Gap: 32px (lg)
```

### List / Table Layout

```
┌──────────────────────────────────────────────────────┐
│ "Actions/objectives I have assigned others" (13)    │
├──────┬─────────────┬─────────┬─────────┬────────────┤
│ icon │ Title       │ Owner   │ Start   │ Deadline   │
├──────┼─────────────┼─────────┼─────────┼────────────┤
│ ⋮⋮   │ Good & Q... │ Eric E. │ 01.01.24│ 31.12.24   │
│ ⋮⋮   │ Acquire 10  │ Eric E. │ 05.06.24│ 31.12.24   │
│ ⋮⋮   │ KPI         │ Liza H. │ 15.12.24│ 31.12.24   │
│ ⋮⋮   │ Give feed   │ Karin E.│ 01.01.25│ 31.12.25   │
└──────┴─────────────┴─────────┴─────────┴────────────┘

Row Height: 56px
Column Spacing: 16px (md)
Alternating Row Colors: White & #F8F6F3 (optional)
Header Font: 12px, SemiBold, #8B8680
Row Font: 14px, Regular, #2D2622
```

### Form Layout

```
┌─────────────────────────────────────────┐
│ "Personal data"                         │
├─────────────────────────────────────────┤
│                                         │
│ [Upload Avatar]                        │
│                                         │
│ Label: "Last name" *                   │
│ ┌─────────────────────────────────────┐│
│ │ Leder                               ││
│ └─────────────────────────────────────┘│
│                                         │
│ Label: "Gender"                        │
│ ┌─────────────────────────────────────┐│
│ │ [Dropdown] Female                   ││
│ └─────────────────────────────────────┘│
│                                         │
│ Label: "Employment status"             │
│ ┌─────────────────────────────────────┐│
│ │ [Dropdown] Employed                 ││
│ └─────────────────────────────────────┘│
│                                         │
│ [Cancel] [Save]                        │
│                                         │
└─────────────────────────────────────────┘

Form Padding: 32px (lg)
Field Gap: 20px
Label Spacing: 8px above input
Button Group: 16px gap between buttons
```

---

## 8. INTERACTIVE STATES & TRANSITIONS

### Button Interactions

```
Default → Hover → Active → (Click) → Disabled

Transition Duration: 200ms
Easing: ease-out (cubic-bezier(0.4, 0, 0.2, 1))

Visual Feedback:
- Hover: Slightly lighter color, increased shadow
- Active: Darker color, pressed appearance
- Disabled: Reduced opacity (50%), cursor: not-allowed
```

### Card Interactions

```
Default → Hover → (Click/Select)

Hover Effect:
├─ Shadow increase: 0 2px 6px → 0 4px 12px
├─ Border color: #E8E5F2 → #D8D5CE
├─ Cursor: pointer
├─ Transition: 0.2s ease

Transition Duration: 150ms
```

### Form Field Interactions

```
Default → Focus → Filled → (Invalid)

Focus State:
├─ Border color: #D8D5CE → #5B4B8A
├─ Box shadow: 0 0 0 3px rgba(91, 75, 138, 0.1)
├─ Background: Stays white
├─ Cursor: text

Filled State:
├─ Value displayed
├─ Label may float up (if floating label pattern)

Invalid State:
├─ Border color: #C41E3A (red)
├─ Error message: 12px, #C41E3A, below field
├─ Background: Slightly tinted #FFF0F2
```

### Animations

```
Page Transitions: 300ms fade-in + slide-up (20px)
Modal Open: 200ms scale (0.95 → 1) + fade-in
Menu Open: 150ms slide-down
Hover Effects: 150ms transform scale(1.02)
Loading: Spinner rotation (linear, 2s)
Notifications: Slide-in from top (300ms) + auto-dismiss (5s)
```

---

## 9. RESPONSIVE DESIGN

### Breakpoints

| Device | Breakpoint | Grid Columns | Use Case |
|---|---|---|---|
| **Mobile** | < 640px | 1-2 columns | Smartphones |
| **Tablet** | 640px - 1024px | 4-6 columns | iPads, tablets |
| **Desktop** | 1024px - 1440px | 8-12 columns | Large screens |
| **Ultra-Wide** | > 1440px | 12 columns (max-width container) | 4K monitors |

### Responsive Adjustments

```
Mobile (< 640px):
├─ Font sizes: -2px (H1: 28px, Body: 12px)
├─ Padding: -8px reduction (cards: 16px)
├─ Grid: Single column, stacked
├─ Buttons: Full width

Tablet (640px - 1024px):
├─ Grid: 2-3 columns
├─ Padding: Reduced
├─ Navigation: Sidebar collapsible

Desktop (> 1024px):
├─ Grid: 3-4 columns
├─ Full padding (24px)
├─ Side-by-side layouts

Ultra-Wide (> 1440px):
├─ Max-width container: 1400px (centered)
├─ Extra spacing around content
```

---

## 10. ACCESSIBILITY GUIDELINES

### Color Contrast

All text must meet WCAG AA standards (minimum 4.5:1 for normal text):

| Combination | Ratio | Status |
|---|---|---|
| #2D2622 on #FFFFFF | 12:1 | ✓ AAA |
| #5C5854 on #FFFFFF | 7:1 | ✓ AA |
| #8B8680 on #FFFFFF | 4.5:1 | ✓ AA |
| #5B4B8A on #F8F6F3 | 5.5:1 | ✓ AA |
| #FFB4D1 on #2D2622 | 3.2:1 | ✗ Fails - use dark text on pink |

### Typography Accessibility

- Minimum font size: 12px (body text: 14px minimum)
- Line height: Minimum 1.5 (22px for 14px text)
- Letter spacing: 0.3px for better readability
- Avoid all-caps for long text (use for labels only)

### Interactive Elements

- Minimum touch target size: 44px × 44px (mobile)
- Keyboard navigation: Tab order should be logical, left-to-right, top-to-bottom
- Focus indicator: 3px solid purple outline, clearly visible
- ARIA labels: All icons should have alt text or aria-label

### Images & Icons

- All images have alt text
- Icons with labels don't need additional alt text
- Decorative icons should have `aria-hidden="true"`

### Motion & Animation

- Respect `prefers-reduced-motion` media query
- Animations should not flash (> 3 times per second)
- No auto-playing videos without controls

---

## 11. DARK MODE SUPPORT (Optional)

For future implementation, here's the dark mode palette:

### Dark Mode Colors

| Component | Light | Dark |
|---|---|---|
| Background | #F8F6F3 | #1A1815 |
| Card | #FFFFFF | #2D2622 |
| Primary Text | #2D2622 | #F8F6F3 |
| Secondary Text | #5C5854 | #B8B5AE |
| Primary Button | #5B4B8A | #7B6FAA (lighter) |
| Border | #E8E5F2 | #403A52 |

**Implementation:** Use CSS custom properties (CSS variables) for easy toggling:

```css
:root {
  --color-bg-primary: #F8F6F3;
  --color-text-primary: #2D2622;
  --color-primary: #5B4B8A;
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-bg-primary: #1A1815;
    --color-text-primary: #F8F6F3;
    --color-primary: #7B6FAA;
  }
}
```

---

## 12. USAGE EXAMPLES

### Example 1: Dashboard Home

```
┌─────────────────────────────────────────────────────────┐
│ Header: "Demo Group HRMS" [Account Settings]          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ┌─────────────────────┐  ┌─────────────────────┐      │
│ │ My tasks            │  │ Quick Actions       │      │
│ │ ───────────────     │  │ ────────────────    │      │
│ │ [Task 1] [14d O]    │  │ [🎯] Goals          │      │
│ │ [Task 2] [7d O]     │  │ [📊] Reports        │      │
│ │ [View all →]        │  │ [👥] My Team        │      │
│ └─────────────────────┘  └─────────────────────┘      │
│                                                         │
│ ┌─────────────────────┐  ┌─────────────────────┐      │
│ │ My Employees (9)    │  │ Key Metrics         │      │
│ │ ───────────────     │  │ ────────────        │      │
│ │ [Avatar] Name       │  │ Attendance: 94%     │      │
│ │ [Avatar] Name       │  │ Engagement: 87%     │      │
│ │ [Avatar] Name       │  │ Turnover: 5%        │      │
│ │ [View all →]        │  │                     │      │
│ └─────────────────────┘  └─────────────────────┘      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Example 2: Employee Profile

```
┌──────────────────────────────────────────┐
│ Personal Data                            │
├──────────────────────────────────────────┤
│                                          │
│  [Avatar Photo]   Employee ID: 10091    │
│  [Edit]                                  │
│                                          │
│  Name: Liv Leder                        │
│  Role: Sales Manager Norway             │
│  Status: Employed                       │
│  Department: Sales                      │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │ Contact Information                │ │
│  │ Email: liv@grace.com               │ │
│  │ Phone: +47 XXX XXX                │ │
│  │ Office: Oslo                       │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌─────────────────────────────────────┐│
│  │ [Edit] [Save Changes]              ││
│  └─────────────────────────────────────┘│
│                                          │
└──────────────────────────────────────────┘
```

### Example 3: Performance Workflow

```
┌───────────────────────────────────────────────┐
│ Performance Dialogue 2024                    │
├───────────────────────────────────────────────┤
│                                               │
│ Welcome to your Performance Dialogue          │
│                                               │
│ [Illustration: Two people discussing]        │
│                                               │
│ Once yearly, all employees conduct...       │
│                                               │
│ Progress: ████░░░░░░░ 40%                    │
│                                               │
│ Sections:                                    │
│ ✓ Job Description (Complete)                 │
│ ✓ CV (Complete)                              │
│ ◯ Objectives (In Progress)                   │
│ ○ Competencies (Not Started)                │
│ ○ Summary (Not Started)                      │
│                                               │
│ [Previous] [Next] [Save & Exit]             │
│                                               │
└───────────────────────────────────────────────┘
```

---

## 13. BRAND PERSONALITY

### Design Principles

1. **Human-Centric:** Real people, real photos, approachable design
2. **Professional:** Purple conveys trust, reliability, and expertise
3. **Clear:** Generous whitespace, uncluttered, easy to scan
4. **Warm:** Cream backgrounds, soft accents, not cold or harsh
5. **Consistent:** Repeatable patterns, predictable interactions
6. **Accessible:** Inclusive design, readable text, keyboard navigation

### Tone & Voice

The interface should feel:
- **Professional but approachable:** Not stiff, not casual
- **Helpful:** Provide context and guidance
- **Respectful:** Of employee time and privacy
- **Transparent:** Clear status and expectations
- **Empowering:** Give employees control and visibility

---

## 14. IMPLEMENTATION CHECKLIST

### Phase 1: Foundation
- [ ] Set up CSS custom properties for colors
- [ ] Define typography scale
- [ ] Create spacing/grid utilities
- [ ] Build button component library
- [ ] Implement card system

### Phase 2: Components
- [ ] Forms (inputs, select, checkbox, radio)
- [ ] Navigation (sidebar, header)
- [ ] Badges and status indicators
- [ ] Modals and overlays
- [ ] Tables and lists

### Phase 3: Patterns
- [ ] Dashboard layouts
- [ ] Profile pages
- [ ] Workflow steps
- [ ] Employee grids
- [ ] Empty states and loading states

### Phase 4: Polish
- [ ] Dark mode (optional)
- [ ] Micro-interactions and animations
- [ ] Accessibility audit (WCAG AA)
- [ ] Responsive design testing
- [ ] Performance optimization

---

## 15. DESIGN TOKENS (FOR DEVELOPERS)

```css
/* Colors */
--color-primary: #5B4B8A;
--color-primary-hover: #6E5FA0;
--color-primary-dark: #3D3461;
--color-primary-light: #E8E5F2;

--color-secondary-pink: #FFB4D1;
--color-secondary-teal: #6DB5B8;
--color-secondary-red: #E85D75;

--color-bg-primary: #F8F6F3;
--color-bg-secondary: #F3F1ED;
--color-bg-card: #FFFFFF;

--color-text-primary: #2D2622;
--color-text-secondary: #5C5854;
--color-text-tertiary: #8B8680;

--color-border: #E8E5F2;
--color-border-light: #D8D5CE;

/* Typography */
--font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
--font-size-h1: 32px;
--font-size-h2: 24px;
--font-size-h3: 18px;
--font-size-body: 14px;
--font-size-label: 12px;

--font-weight-regular: 400;
--font-weight-medium: 500;
--font-weight-semibold: 600;
--font-weight-bold: 700;

/* Spacing */
--spacing-xs: 4px;
--spacing-sm: 8px;
--spacing-md: 16px;
--spacing-lg: 24px;
--spacing-xl: 32px;

/* Shadows */
--shadow-sm: 0 2px 6px rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 12px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.15);

/* Border Radius */
--radius-sm: 4px;
--radius-md: 6px;
--radius-lg: 8px;
--radius-full: 50%;
```

---

## 16. WHITE-LABELING GUIDELINES

### Overview

As a **multi-tenant SaaS platform**, Alvoraa HRMS must support white-labeling to allow enterprise customers (like Demo Group, and future customers) to customize the application with their own branding. This section defines which elements are customizable and which must remain consistent for system integrity.

### White-Labeling Strategy

**Two-Tier Customization Approach:**

1. **Tier 1 - Lite White-Labeling** (Standard for most customers)
   - Logo and company name
   - Primary color theme
   - Basic text customizations (terminology)

2. **Tier 2 - Full White-Labeling** (Premium, for enterprise customers)
   - Complete color palette customization
   - Custom typography (font families)
   - Custom imagery and illustrations
   - Domain/URL branding
   - Email template customization

---

### SECTION A: CUSTOMIZABLE ELEMENTS (Customer Controls)

#### A.1 Logo & Branding

| Element | Customizable | Guidelines | Notes |
|---|---|---|---|
| **Company Logo** | ✓ YES | Max 200px wide, PNG/SVG, transparent background | Used in header, login page, emails |
| **Company Name** | ✓ YES | Max 40 characters | Replaces "Demo Group HRMS" in header |
| **Favicon** | ✓ YES | 32x32px ICO or PNG | Browser tab icon |
| **Product Name** | ✓ YES (Limited) | Max 50 characters | e.g., "Demo Talent Management System" |

**Implementation:**
```
Admin Settings → Branding → Logo Upload
├─ Upload logo (max 2MB)
├─ Set company name
├─ Select logo placement (top-left, centered)
└─ Preview in real-time
```

**Technical Requirements:**
- Logo should scale responsively (mobile → desktop)
- Must not distort below 100px width
- Should work on both light and dark backgrounds
- SVG preferred for scalability (PNG fallback)

---

#### A.2 Primary Color Customization

| Component | Customizable | Default | Range |
|---|---|---|---|
| **Primary Button Color** | ✓ YES | #5B4B8A (Purple) | Full hex color picker |
| **Button Hover State** | ⚙️ AUTO | 10% lighter than primary | Auto-calculated |
| **Primary Text Color** | ✓ YES | #2D2622 (Dark Charcoal) | High-contrast colors only |
| **Link Color** | ✓ YES | Primary button color | Must meet WCAG AA (4.5:1) |
| **Accent Color** | ✓ YES | #6DB5B8 (Teal) | For success, completion |

**Color Customization Interface:**

```
Admin Settings → Branding → Colors
├─ Primary Color Picker
│  ├─ Current: #5B4B8A
│  ├─ Preview button with this color
│  └─ Auto-preview across UI
├─ Text Color (with contrast checker)
├─ Link Color (with contrast checker)
├─ Accent Color (with contrast checker)
└─ [Reset to Default] [Save Changes]

Live Preview Pane:
├─ Sample button
├─ Sample link
├─ Sample card with colored accent
├─ WCAG Compliance Status ✓/✗
```

**Validation Rules:**
- All colors must pass WCAG AA contrast ratio (4.5:1 minimum)
- System auto-warns if contrast fails
- Primary and text colors cannot be the same
- Accent color must differentiate from primary

**Color Application:**
```
Primary Color (#5B4B8A) is used for:
├─ Primary buttons
├─ Link text
├─ Active navigation
├─ Headers/headings
└─ Focus indicators

Hover State (auto-generated):
├─ Calculated as: Lighten primary by 10%
├─ Applied to: Button hover, link hover, card hover

Accent Color (#6DB5B8) is used for:
├─ Success badges
├─ Completion checkmarks
├─ Positive indicators
└─ Secondary highlights
```

---

#### A.3 Secondary Color Palette

| Element | Customizable | Default | Purpose |
|---|---|---|---|
| **Alert/Warning Color** | ✓ YES | #FFB4D1 (Soft Pink) | Overdue, warnings, time-sensitive |
| **Error Color** | ✓ YES | #E85D75 (Coral Red) | Errors, critical alerts, denials |
| **Info Color** | ✓ YES | #4A90E2 (Blue) | Information, help, guidance |
| **Success Color** | ✓ YES | #6DB5B8 (Teal) | Success messages, completion |

**Semantic Color Mapping:**
```
Status-to-Color Mapping (Customizable per Tenant):
├─ Overdue → Alert Color
├─ Completed → Success Color
├─ In Progress → Info Color
├─ Blocked → Error Color
└─ Pending → Secondary/Gray Color
```

---

#### A.4 Background & Surface Colors

| Element | Customizable | Default | Notes |
|---|---|---|---|
| **Main Background** | ✗ NO (Fixed) | #F8F6F3 (Warm Cream) | System-wide, not customizable |
| **Card Background** | ✗ NO (Fixed) | #FFFFFF (White) | Maintains contrast & readability |
| **Secondary Surface** | ✗ NO (Fixed) | #F3F1ED (Light Gray) | Structural consistency |

**Reason for Fixed Backgrounds:**
- Ensures WCAG AA contrast ratios remain valid
- Maintains readability across all devices
- Prevents over-branding that could break usability

---

#### A.5 Typography Customization (Premium Tier)

| Element | Customizable | Default | Options |
|---|---|---|---|
| **Font Family** | ✓ YES (Premium) | Inter/Segoe UI | Google Fonts, Adobe Fonts, custom |
| **Font Scale** | ✗ NO (Fixed) | 32px→12px hierarchy | System-wide scale |
| **Font Weights** | ✗ NO (Fixed) | 400, 500, 600, 700 | Maintains hierarchy |

**Premium Font Options:**
```
Curated font families (pre-tested for readability):
├─ Modern Sans-Serif
│  ├─ Inter (default, system font)
│  ├─ Poppins (friendly, rounded)
│  └─ Montserrat (geometric, elegant)
├─ Professional Sans-Serif
│  ├─ IBM Plex Sans (corporate)
│  └─ Roboto (neutral, scalable)
└─ Custom Font Upload (advanced)
   ├─ WOFF2 format required
   └─ Must include all weights (400, 500, 600, 700)
```

**Admin Interface:**
```
Admin Settings → Branding → Typography (Premium)
├─ Font Family Dropdown
│  └─ Preview with each font
├─ Upload Custom Font (optional)
└─ [Preview Full Page with Font]
```

---

#### A.6 Text & Terminology Customization

| Element | Customizable | Default | Max Length |
|---|---|---|---|
| **App Title** | ✓ YES | "Demo Group HRMS" | 50 chars |
| **Department Name** | ✓ YES | "HR Department" | 30 chars |
| **Employee Title** | ✓ YES | "Employee" | 20 chars |
| **Manager Title** | ✓ YES | "Manager" | 20 chars |
| **Custom Modules** | ✓ YES | "Goals", "Performance" | Per module |

**Terminology Customization Interface:**
```
Admin Settings → Customization → Terminology
├─ General
│  ├─ Product name: [________]
│  └─ Organization name: [________]
├─ Roles & Terms
│  ├─ "Employee" → [________]
│  ├─ "Manager" → [________]
│  └─ "Department" → [________]
├─ Module Names (if custom)
└─ [Save & Apply Across System]
```

---

### SECTION B: LOCKED ELEMENTS (Non-Customizable)

These elements must **remain consistent** for legal, technical, and UX reasons:

| Element | Why Locked | Impact if Changed |
|---|---|---|
| **Layout Structure** | Technical stability | Could break responsive design |
| **Navigation Pattern** | User experience | Users would get lost in each tenant |
| **Form Fields** | Data integrity | Fields must exist for database |
| **Button Placement** | Accessibility | Could break keyboard navigation |
| **Typography Scale** | Readability | Could violate accessibility standards |
| **Component Spacing** | Responsive design | Could break mobile layouts |
| **Icons** | Consistency | Different meanings across tenants |
| **Security Elements** | Legal compliance | Auth, encryption, audit trails |
| **Data Fields** | GDPR compliance | Required for data privacy |

**Why This Matters:**
- **Consistency:** Users switching between customers see familiar patterns
- **Compliance:** Legal and security requirements must be met
- **Quality:** Prevents customers from breaking their own applications
- **Support:** Reduces customer support burden

---

### SECTION C: WHITE-LABELING IMPLEMENTATION ARCHITECTURE

#### C.1 Tenant-Specific Styling

```javascript
// CSS Variables per Tenant (Loaded at Login/Initialization)

:root {
  // Brand Colors (Customizable)
  --tenant-color-primary: #5B4B8A;
  --tenant-color-primary-hover: #6E5FA0;
  --tenant-color-primary-dark: #3D3461;
  --tenant-color-accent: #6DB5B8;
  --tenant-color-alert: #FFB4D1;
  --tenant-color-error: #E85D75;
  
  // Brand Assets (Customizable)
  --tenant-logo-url: url('/logos/default-logo.svg');
  --tenant-font-family: 'Inter', system-ui, sans-serif;
  
  // Fixed Structural Colors (Locked)
  --app-bg-primary: #F8F6F3;
  --app-bg-card: #FFFFFF;
  --app-text-primary: #2D2622;
  --app-text-secondary: #5C5854;
}
```

**How It Works:**
1. User logs in → System queries tenant configuration
2. CSS variables dynamically loaded based on tenant ID
3. All components use CSS variables (not hardcoded colors)
4. No page reload needed (CSS applies immediately)

#### C.2 Tenant Configuration Database Schema

```sql
CREATE TABLE tenant_branding (
  tenant_id UUID PRIMARY KEY,
  company_name VARCHAR(50),
  logo_url VARCHAR(500),
  
  -- Colors (Customizable)
  primary_color HEX DEFAULT '#5B4B8A',
  primary_hover_color HEX DEFAULT '#6E5FA0',
  text_color HEX DEFAULT '#2D2622',
  link_color HEX DEFAULT '#5B4B8A',
  accent_color HEX DEFAULT '#6DB5B8',
  alert_color HEX DEFAULT '#FFB4D1',
  error_color HEX DEFAULT '#E85D75',
  
  -- Typography (Premium Tier)
  font_family VARCHAR(100) DEFAULT 'Inter',
  font_custom_url VARCHAR(500) NULL,
  
  -- Terminology
  employee_term VARCHAR(20) DEFAULT 'Employee',
  manager_term VARCHAR(20) DEFAULT 'Manager',
  department_term VARCHAR(20) DEFAULT 'Department',
  
  -- Customization Tier
  tier ENUM('lite', 'premium') DEFAULT 'lite',
  
  -- Audit
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

#### C.3 Admin Panel for White-Labeling

```
┌─────────────────────────────────────────────────────┐
│ Admin Dashboard > Branding Settings                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│ 📋 BRANDING CONFIGURATION                          │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Logo & Identity                                 │ │
│ ├─────────────────────────────────────────────────┤ │
│ │ Company Logo:                                   │ │
│ │ [Upload Logo] [Download Current]                │ │
│ │                                                 │ │
│ │ Company Name: [Demo Group       ]              │ │
│ │                                                 │ │
│ │ App Title: [Demo Group HRMS     ]              │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Color Customization                             │ │
│ ├─────────────────────────────────────────────────┤ │
│ │ Primary Button Color: [⚫ #5B4B8A] [Color Picker]│ │
│ │ Preview: [Sample Button with Color]             │ │
│ │ Contrast: ✓ WCAG AA Compliant                   │ │
│ │                                                 │ │
│ │ Alert/Warning Color: [⚫ #FFB4D1] [Color Picker]│ │
│ │ Preview: [Sample Badge]                        │ │
│ │                                                 │ │
│ │ Accent Color: [⚫ #6DB5B8] [Color Picker]       │ │
│ │ Preview: [Sample Checkmark]                    │ │
│ │                                                 │ │
│ │ [Reset to Default] [Save Changes]              │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Typography (Premium Tier)                       │ │
│ ├─────────────────────────────────────────────────┤ │
│ │ Font Family: [Dropdown: Inter ▼]                │ │
│ │ Options: Inter, Poppins, IBM Plex, Montserrat │ │
│ │ Preview: [Sample text in selected font]       │ │
│ │                                                 │ │
│ │ Upload Custom Font: [Choose File]              │ │
│ │ (WOFF2 required)                               │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Terminology                                     │ │
│ ├─────────────────────────────────────────────────┤ │
│ │ Employee Title: [Employee        ]              │ │
│ │ Manager Title:  [Manager         ]              │ │
│ │ Department:     [Department      ]              │ │
│ │                                                 │ │
│ │ [Save & Apply]                                  │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ ✋ LOCKED ELEMENTS (Cannot Customize)            │ │
│ ├─────────────────────────────────────────────────┤ │
│ │ • Layout & Navigation                          │ │
│ │ • Component Spacing & Sizing                   │ │
│ │ • Form Fields & Data Structure                │ │
│ │ • Accessibility Features (WCAG AA)             │ │
│ │ • Security & Compliance Elements               │ │
│ │                                                 │ │
│ │ [Learn More About White-Labeling]              │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ [Cancel] [Preview Full App] [Save & Apply]        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

### SECTION D: WHITE-LABELING EXAMPLES

#### Example 1: Demo Group (Current Customer)

```
┌─────────────────────────────────────┐
│ 🏢 Demo Group HRMS                 │
├─────────────────────────────────────┤
│                                     │
│ ┌──────────────────────────────┐   │
│ │ My tasks              [15]    │   │
│ │ ──────────────────────────── │   │
│ │ [Purple Button: Create New]   │   │
│ │ Salary review                │   │
│ │ [Badge: 14 days overdue]     │   │
│ └──────────────────────────────┘   │
│                                     │

Customizations Applied:
├─ Logo: Demo Group logo
├─ Company Name: "Demo Group HRMS"
├─ Primary Color: #5B4B8A (Purple)
├─ Font: Inter (default)
└─ Terminology: Employee, Manager, Delivery Team
```

#### Example 2: Hypothetical Customer - TechCorp (Premium Tier)

```
┌─────────────────────────────────────┐
│ 🚀 TechCorp Talent Platform         │
├─────────────────────────────────────┤
│                                     │
│ ┌──────────────────────────────┐   │
│ │ My tasks              [15]    │   │
│ │ ──────────────────────────── │   │
│ │ [TEAL Button: Create New]     │   │
│ │ Salary review                │   │
│ │ [Badge: 14 days overdue]     │   │
│ └──────────────────────────────┘   │
│                                     │

Customizations Applied:
├─ Logo: TechCorp logo
├─ Company Name: "TechCorp Talent Platform"
├─ Primary Color: #00A8CC (TechCorp Teal)
├─ Alert Color: #FF6B35 (TechCorp Orange)
├─ Font: Montserrat (premium font)
├─ Tier: Premium
└─ Terminology: "Team Member", "Team Lead", "Org Unit"
```

#### Example 3: Hypothetical Customer - RetailPlus (Lite Tier)

```
┌─────────────────────────────────────┐
│ 🛍️ RetailPlus HR                    │
├─────────────────────────────────────┤
│                                     │
│ ┌──────────────────────────────┐   │
│ │ My tasks              [15]    │   │
│ │ ──────────────────────────── │   │
│ │ [RED Button: Create New]      │   │
│ │ Salary review                │   │
│ │ [Badge: 14 days overdue]     │   │
│ └──────────────────────────────┘   │
│                                     │

Customizations Applied (Lite Tier):
├─ Logo: RetailPlus logo
├─ Company Name: "RetailPlus HR System"
├─ Primary Color: #D32F2F (RetailPlus Red)
├─ Font: Inter (standard)
├─ Tier: Lite
└─ Terminology: "Associate", "Supervisor", "Store"
```

---

### SECTION E: WHITE-LABELING FEATURE PARITY

#### Feature Matrix: Customization by Tier

| Feature | Lite Tier | Premium Tier | Notes |
|---|---|---|---|
| Logo upload | ✓ | ✓ | Primary branding element |
| Company name | ✓ | ✓ | Replaces default company name |
| Primary color | ✓ | ✓ | Button, link, navigation |
| Secondary colors (4) | ✓ | ✓ | Alert, error, info, success |
| Terminology | ✓ | ✓ | Employee, manager, department |
| Custom font | ✗ | ✓ | Premium feature, premium support |
| Email templates | ✗ | ✓ | Custom email branding |
| Custom domain | ✗ | ✓ | Branded login page URL |
| API white-label | ✗ | ✓ | Remove Alvoraa branding from API |
| Support & SLA | Standard | Premium | Priority support included |

---

### SECTION F: IMPLEMENTATION ROADMAP

#### Phase 1: Lite White-Labeling (MVP)
**Timeline: Weeks 1-4**

```
✓ Logo upload & display in header
✓ Company name customization
✓ Primary color picker (buttons, links)
✓ Color validation (WCAG AA)
✓ Terminology replacement (Employee, Manager)
✓ Admin UI for branding settings
✓ CSS variables system
✓ Testing with first customer (Demo Group)
```

#### Phase 2: Full Color Customization
**Timeline: Weeks 5-8**

```
✓ Secondary color customization (alert, error, info)
✓ Semantic color mapping to statuses
✓ Color preview across all UI elements
✓ Real-time CSS updates (no reload)
✓ Export/import color profiles
✓ Color history & rollback
```

#### Phase 3: Premium Typography (Optional)
**Timeline: Weeks 9-12**

```
✓ Google Fonts integration
✓ Custom font upload (WOFF2)
✓ Font preview across app
✓ Font fallback management
✓ Performance optimization (font loading)
```

#### Phase 4: Advanced Branding (Future)
**Timeline: Q2+ 2026**

```
✓ Custom email templates
✓ Custom login page branding
✓ Custom domain support
✓ API white-labeling (remove Alvoraa attribution)
✓ Favicon customization
✓ Illustration customization (onboarding, empty states)
```

---

### SECTION G: BEST PRACTICES & GUIDELINES

#### For Customers (White-Labeling Users)

1. **Color Selection:**
   - Stick to brand colors (1-2 primary, 1-2 secondary)
   - Ensure sufficient contrast (WCAG AA minimum)
   - Test colors on mobile devices
   - Consider colorblind accessibility

2. **Logo Optimization:**
   - Use high-resolution logos (SVG recommended)
   - Test at all sizes (100px → 200px)
   - Use logos with transparent backgrounds
   - Ensure logo works on both light and dark backgrounds

3. **Typography (Premium):**
   - Choose professional fonts (avoid decorative)
   - Test readability at small sizes (12px+)
   - Stick to 1-2 fonts maximum
   - Ensure custom fonts load quickly

4. **Terminology Consistency:**
   - Use industry-standard terms
   - Keep terms short (< 20 characters)
   - Test terminology across all screens
   - Document custom terminology for users

#### For Alvoraa (Platform Developers)

1. **CSS Architecture:**
   - Use CSS custom properties for all brandable colors
   - Never hardcode brand colors in components
   - Create utility classes for color variants
   - Test color contrast in WCAG validator

2. **Performance:**
   - Load tenant branding before page render
   - Cache branding config in browser/CDN
   - Lazy-load custom fonts (Google Fonts, etc.)
   - Minimize CSS/JS for branding logic

3. **Security:**
   - Validate all color inputs (hex format)
   - Sanitize logo uploads (virus scan, file type check)
   - Prevent CSS injection via branding settings
   - Log all branding changes for audit trail

4. **Testing:**
   - Test with multiple brand color schemes
   - Test on mobile, tablet, desktop
   - Test with screen readers (accessibility)
   - Test with high-contrast mode enabled
   - Test with colorblind simulator

---

### SECTION H: WHITE-LABELING API (For Integrations)

Developers can programmatically customize branding via REST API:

```bash
# Update Tenant Branding

PUT /api/v1/admin/branding
Authorization: Bearer TOKEN
Content-Type: application/json

{
  "company_name": "Demo Group",
  "primary_color": "#5B4B8A",
  "alert_color": "#FFB4D1",
  "accent_color": "#6DB5B8",
  "employee_term": "Employee",
  "manager_term": "Manager",
  "logo_url": "https://cdn.example.com/logos/grace-group.svg"
}

# Response
200 OK
{
  "tenant_id": "tenant_12345",
  "updated_at": "2026-01-15T10:30:00Z",
  "changes_applied": true
}
```

---

### SECTION I: WHITE-LABELING SUPPORT & TROUBLESHOOTING

| Issue | Solution | Owner |
|---|---|---|
| Logo not showing | Clear cache, check file format (SVG/PNG) | Customer |
| Colors not applying | Verify hex format (#XXXXXX), test in different browser | Alvoraa Support |
| Text contrast failing | System auto-warns; choose different shade | Customer |
| Font not loading | Check WOFF2 format, verify CDN access | Alvoraa DevOps |
| Mobile responsiveness broken | Logo may be too wide; resize or use icon instead | Alvoraa Design |

---

### SECTION J: COMPLIANCE & LEGAL

#### White-Labeling Terms

1. **Trademark & Branding Rights**
   - Customer retains rights to their own branding
   - Alvoraa retains rights to underlying platform
   - Customer cannot remove Alvoraa copyright notice (in small footer)

2. **Liability**
   - Alvoraa not liable for customer branding choices
   - Customer responsible for ensuring brand color accessibility
   - Alvoraa may restrict "offensive" branding (case-by-case)

3. **Support Scope**
   - Alvoraa supports technical white-labeling setup
   - Alvoraa does NOT provide design/branding advice
   - Customer responsible for brand consistency

---

## CONCLUSION

This white-labeling framework enables Alvoraa HRMS to serve multiple enterprise customers while maintaining design consistency and platform stability. By carefully balancing customization with control, we create a system that feels personal to each customer while remaining maintainable and accessible.

This design theme transforms the Demo Group HRMS into a **modern, professional, human-centric enterprise application**. The purple-and-teal color scheme conveys trust and professionalism, while warm cream backgrounds and generous whitespace make the interface approachable and easy to use.

The design supports 200 employees ranging from delivery personnel to management, with clear hierarchies, accessible typography, and interactive patterns that guide users through complex HR workflows.

**Next Steps:**
1. Build component library in your chosen framework (React, Vue, Angular, etc.)
2. Implement design tokens as CSS variables
3. Create Figma design system file (mirror of this guide)
4. Conduct accessibility audit (WCAG AA compliance)
5. Test with real users and refine based on feedback

