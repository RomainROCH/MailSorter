# MailSorter Labs Design System

> **Palette B - High Tech Identity**

This document describes the visual identity system for MailSorter, including color palettes, theme switching, and usage guidelines.

---

## 🎨 Color Palette

### Semantic Colors (Consistent across themes)

| Variable | Hex | Usage |
|----------|-----|-------|
| `--ms-success` | ![#10B981](https://img.shields.io/badge/-10B981-10B981?style=flat-square) `#10B981` | Success states, sorted emails |
| `--ms-error` | ![#EF4444](https://img.shields.io/badge/-EF4444-EF4444?style=flat-square) `#EF4444` | Errors, alerts, destructive actions |
| `--ms-info` | ![#3B82F6](https://img.shields.io/badge/-3B82F6-3B82F6?style=flat-square) `#3B82F6` | Information, links, neutral highlights |

---

### Dark Mode (Default - High Tech)

| Variable | Hex | Usage |
|----------|-----|-------|
| `--ms-bg` | ![#0F172A](https://img.shields.io/badge/-0F172A-0F172A?style=flat-square) `#0F172A` | Deep navy background |
| `--ms-text` | ![#F1F5F9](https://img.shields.io/badge/-F1F5F9-F1F5F9?style=flat-square) `#F1F5F9` | Ghost white text |
| `--ms-primary` | ![#2DD4BF](https://img.shields.io/badge/-2DD4BF-2DD4BF?style=flat-square) `#2DD4BF` | Teal - Primary actions |
| `--ms-secondary` | ![#475569](https://img.shields.io/badge/-475569-475569?style=flat-square) `#475569` | Slate - Borders, surfaces |
| `--ms-accent` | ![#F59E0B](https://img.shields.io/badge/-F59E0B-F59E0B?style=flat-square) `#F59E0B` | Amber - CTA, Pro features |

---

### Light Mode (High Contrast)

| Variable | Hex | Usage |
|----------|-----|-------|
| `--ms-bg` | ![#D6DEF0](https://img.shields.io/badge/-D6DEF0-D6DEF0?style=flat-square) `#D6DEF0` | Light blue-gray background |
| `--ms-text` | ![#060A0E](https://img.shields.io/badge/-060A0E-060A0E?style=flat-square) `#060A0E` | Technical black text |
| `--ms-primary` | ![#0D9488](https://img.shields.io/badge/-0D9488-0D9488?style=flat-square) `#0D9488` | Dark teal for readability |
| `--ms-secondary` | ![#95A3B7](https://img.shields.io/badge/-95A3B7-95A3B7?style=flat-square) `#95A3B7` | Light slate |
| `--ms-accent` | ![#F59F0A](https://img.shields.io/badge/-F59F0A-F59F0A?style=flat-square) `#F59F0A` | Amber (slightly adjusted) |

---

## 🔄 Theme Switching

### Available Themes

| Theme | Class | Description |
|-------|-------|-------------|
| **Palette B Dark** | (default) | Modern high-tech look, dark mode |
| **Palette B Light** | `.theme-light` | High contrast light mode |
| **Classic Dark** | `.theme-classic` | Legacy Photon-inspired theme |
| **Classic Light** | `.theme-classic.theme-light` | Legacy light mode |

### Usage

```html
<!-- Default: Palette B Dark -->
<html>

<!-- Palette B Light Mode -->
<html class="theme-light">

<!-- Classic Theme (Photon-based) -->
<html class="theme-classic">

<!-- Classic Light -->
<html class="theme-classic theme-light">
```

### System Preference

The theme automatically respects `prefers-color-scheme` unless overridden by a class:

```css
/* Automatically switches based on OS preference */
@media (prefers-color-scheme: light) {
  :root:not(.theme-dark):not(.theme-classic) {
    /* Light mode applied */
  }
}
```

---

## 🧩 Components

### Buttons

```html
<!-- Primary action (Teal) -->
<button class="ms-button ms-button-primary">Sort Emails</button>

<!-- Pro/Accent action (Amber) -->
<button class="ms-button ms-button-accent">Upgrade to Pro</button>
<button class="ms-button ms-button-pro">Pro Feature</button>

<!-- Status buttons -->
<button class="ms-button ms-button-success">Confirm</button>
<button class="ms-button ms-button-danger">Delete</button>
```

### Status Badges

```html
<span class="ms-status-badge ms-status-badge-success">Sorted</span>
<span class="ms-status-badge ms-status-badge-error">Error</span>
<span class="ms-status-badge ms-status-badge-warning">Warning</span>
<span class="ms-status-badge ms-status-badge-info">Processing</span>
<span class="ms-status-badge ms-status-badge-pro">Pro</span>
```

### Category Badges

```html
<span class="ms-category-badge ms-category-badge-sorted">✓ Sorted</span>
<span class="ms-category-badge ms-category-badge-pending">⏳ Pending</span>
<span class="ms-category-badge ms-category-badge-error">⚠ Failed</span>
```

---

## 📝 Documentation Badges

For README and docs, use shields.io with Palette B colors:

```markdown
<!-- Version (Teal) -->
![Version](https://img.shields.io/badge/version-1.1.0-2DD4BF?style=flat-square)

<!-- Status Stable (Success Green) -->
![Status](https://img.shields.io/badge/status-stable-10B981?style=flat-square)

<!-- Alert/Warning (Amber) -->
![Alert](https://img.shields.io/badge/alert-breaking_change-F59E0B?style=flat-square)

<!-- Info (Blue) -->
![Info](https://img.shields.io/badge/info-beta-3B82F6?style=flat-square)

<!-- Error (Red) -->
![Error](https://img.shields.io/badge/error-deprecated-EF4444?style=flat-square)
```

**Preview:**

![Version](https://img.shields.io/badge/version-1.1.0-2DD4BF?style=flat-square)
![Status](https://img.shields.io/badge/status-stable-10B981?style=flat-square)
![Alert](https://img.shields.io/badge/alert-breaking_change-F59E0B?style=flat-square)
![Info](https://img.shields.io/badge/info-beta-3B82F6?style=flat-square)

---

## 📐 Design Tokens Reference

### Full Variable List

```css
/* Palette B Semantic Aliases */
--ms-bg          /* Background */
--ms-text        /* Primary text */
--ms-primary     /* Primary brand color */
--ms-secondary   /* Secondary/border color */
--ms-accent      /* Accent/CTA color */
--ms-success     /* Success states */
--ms-error       /* Error states */
--ms-info        /* Info states */

/* Extended Color System */
--ms-color-primary
--ms-color-primary-hover
--ms-color-primary-active
--ms-color-primary-light

--ms-color-accent
--ms-color-accent-hover
--ms-color-accent-light

--ms-color-success
--ms-color-success-light
--ms-color-warning
--ms-color-warning-light
--ms-color-error
--ms-color-error-light
--ms-color-info
--ms-color-info-light

/* Text */
--ms-color-text
--ms-color-text-secondary
--ms-color-text-disabled
--ms-color-text-on-primary
--ms-color-text-link

/* Surfaces */
--ms-color-background
--ms-color-surface
--ms-color-surface-hover
--ms-color-surface-active
--ms-color-border
--ms-color-border-strong

/* Status Indicators */
--ms-status-connected
--ms-status-disconnected
--ms-status-processing
--ms-status-warning
```

---

## ✅ Accessibility

The design system includes:

- **High Contrast Mode** (`prefers-contrast: more`)
- **Forced Colors Mode** (`forced-colors: active`)
- **Focus indicators** with visible outlines
- **WCAG 2.1 AA** contrast ratios

---

*MailSorter Labs Design System v1.0 - January 2026*
