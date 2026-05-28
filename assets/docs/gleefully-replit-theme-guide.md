# Glee-fully Personalizable Tools™ — Replit App Theme

Reverse-engineered from `assets/css/theme.css` (`.glee-main` overrides).
Enter these values into the **Manage app themes** panel field by field.

---

## FOUNDATION — Colors

| Field | Value | Notes |
|---|---|---|
| Background color | `#f6f2ee` | OKH Paper — the warm cream page canvas |
| Text color | `#2e2b29` | Rich espresso — primary readable text |
| Muted background color | `#fdfbf7` | Lightest paper surface — cards and panels |
| Muted text color | `#6b6b6b` | Warm gray — subdued/secondary text |

---

## FOUNDATION — Typography

| Field | Value | Notes |
|---|---|---|
| Sans-serif font | `DM Sans` | Primary body font — loaded from Google Fonts |
| Serif font | `Georgia` | No serif used in this design; nearest universal fallback |
| Monospace font | `Menlo` | No monospace in this design; browser/system default |

> **Note on fonts:** The site uses a two-font display system:
> - **Fredoka** — playful rounded display font for H1/H2 headings on branch/twig pages
> - **DM Sans** — clean, modern body text throughout
>
> Both are Google Fonts. Load them via:
> ```
> https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600&family=DM+Sans:wght@400;500;600&display=swap
> ```
> If the Replit theme panel does not list Fredoka or DM Sans by name, select **Poppins** (headings) and **Open Sans** (body) as the closest available substitutes.

---

## FOUNDATION — Shape & Spacing

| Field | Value | Notes |
|---|---|---|
| Border radius | `0.75` rem | Standard card/component radius (`--radius-md`). Buttons use 999px pills. |

---

## COMPONENTS — Actions

| Field | Value | Notes |
|---|---|---|
| Primary background | `#d35b2d` | Glee Rust — primary CTA, active nav underline start |
| Primary text | `#0f172a` | Dark ink — high contrast on rust/orange |
| Secondary background | `#2a2320` | OKH Espresso — dark complement surface |
| Secondary text | `#f6f2ee` | Paper — readable on espresso |
| Accent background | `#f3b932` | Glee Gold — nav underline end, highlight color |
| Accent text | `#2e2b29` | Espresso — dark text on gold |
| Destructive background | `#d94f63` | Coral-red — used in the site CSS for error states |
| Destructive text | `#ffffff` | White — readable on coral |

> **Primary CTA gradient** (used on `.btn-primary`):
> `linear-gradient(90deg, #d35b2d, #f3b932)` — Glee Rust → Glee Gold

---

## COMPONENTS — Forms

| Field | Value | Notes |
|---|---|---|
| Input | `#fdfbf7` | Lightest paper surface — inputs blend into page |
| Border | `#d7d7d7` | Soft warm gray — visible on cream backgrounds |
| Focus Border | `#d35b2d` | Glee Rust — matches the site's `outline: 2px solid var(--color-accent)` focus ring |

---

## COMPONENTS — Containers

| Field | Value | Notes |
|---|---|---|
| Card background | `#fdfbf7` | `--color-surface` — the lightest paper, used for all cards and panels on the site |
| Card text | `#2e2b29` | `--color-fg` — rich espresso, primary readable text |
| Popover background | `#fdfbf7` | Same as card surface — consistent floating panel treatment |
| Popover text | `#2e2b29` | Espresso — consistent with all foreground text |

---

## COMPONENTS — Charts

The five chart colors are drawn directly from the site's retro stripe palette, in descending visual weight. This means any generated chart will feel native to the brand rather than using generic defaults.

| Field | Value | Source token | Role in stripe band |
|---|---|---|---|
| Chart 1 | `#d35b2d` | `glee-rust` | Primary — the signature Glee accent |
| Chart 2 | `#1c3a34` | `--okh-teal` | Structural — deepest retro stripe |
| Chart 3 | `#f3b932` | `glee-gold` | Highlight — brightest warm tone |
| Chart 4 | `#676a2c` | `--okh-olive` | Mid — earthy muted green |
| Chart 5 | `#a06e28` | `--okh-ochre` | Warm — amber-brown mid-tone |

---

## Full Color Palette Reference

These are all named tokens from `theme.css`. Use them when building any new app in this workspace.

| Token name | Hex | Role |
|---|---|---|
| `--okh-paper` | `#f6f2ee` | Warm cream — page canvas / background |
| `--color-surface` | `#fdfbf7` | Lightest paper — card and panel surface |
| `--color-surface-soft` | `#f6f2ee` | Standard paper — nested panels, inputs |
| `--color-fg` | `#2e2b29` | Rich espresso — primary body text |
| `--color-muted` | `#6b6b6b` | Warm gray — captions, secondary text |
| `glee-rust` | `#d35b2d` | Glee Rust — primary CTA / link accent / focus ring |
| `glee-gold` | `#f3b932` | Glee Gold — gradient end / highlight |
| `--okh-orange` | `#c46a2c` | OKH Rust-orange — shared CTA base |
| `--okh-amber` | `#e6a03c` | Amber gold — shared secondary accent |
| `--okh-teal` | `#1c3a34` | Deep forest teal — retro stripe 1 |
| `--okh-olive` | `#676a2c` | Muted olive — retro stripe 2 |
| `--okh-ochre` | `#a06e28` | Warm brown-gold — retro stripe 3 |
| `--okh-rust` | `#5b3a27` | Dark rust — retro stripe 4 |
| `--okh-espresso` | `#2a2320` | Darkest tone — dark mode bg / secondary btn |
| `--color-border` | `#d7d7d7` | Soft border — form fields, card edges |
| **Nav gradient** | `linear-gradient(90deg, #d35b2d, #f3b932)` | Active nav underline, Glee signature stripe |
| **Retro stripe band** | Teal → Olive → Ochre → Rust → Espresso | The 5-stripe hero visual identity |

---

## Color Accessibility Rules

These rules are a QA/QC gate for any editor adding or changing colored text on this site.
They come from the accessibility audit in `LIVE_SITE_EVALUATION_2026-05-26.md` §5.5.

### Accent color contrast ratios (against paper background `#f6f2ee`)

| Color | Hex | Ratio | WCAG AA normal text (4.5:1) | WCAG AA large / UI (3:1) |
|---|---|---|---|---|
| GLEE coral | `#d94f63` | 3.37 : 1 | Fail | Pass |
| Orange accent | `#d35b2d` | 3.55 : 1 | Fail | Pass |
| Espresso text on coral btn | `#2e2b29` on `#d94f63` | 3.51 : 1 | Fail | Pass |
| Deep rust | `#9e3b2e` | 6.05 : 1 | Pass | Pass |
| Near-black | `#0d2b3a` | 13.24 : 1 | Pass | Pass |

"Large text" per WCAG 2.1: 18.67 px normal weight, or 14 px bold (equivalent to 18pt / 14pt bold).
Button text at `font-size: 0.95rem; font-weight: 600` qualifies as large text. All current button uses pass.

### Editorial rule (enforced)

> `var(--color-accent)` (`#d94f63` / `#d35b2d`) must not be used as the sole color signal
> for normal-weight body text smaller than 18.67 px.

**Where accent color IS permitted:**

- `.btn-primary`, `.btn-quiet` — button text (≥ 14 px bold, qualifies as large text)
- Headings H1–H3 at any size that meets the large-text threshold
- UI controls (borders, focus rings, icons used alongside text labels)
- Decorative elements (stripes, illustrations) where color is not the sole information carrier

**Where accent color is NOT permitted:**

- Normal-weight (`font-weight: 400–500`) inline body text
- Paragraph copy, list items, captions, labels at default body size (1rem / 16 px)
- Any context where a color-blind or low-vision user could lose meaning if the color is removed

### Safe alternatives for tinted body text

If you need colored body text, use these tokens instead — all pass 4.5:1 against `#f6f2ee`:

| Purpose | Token | Hex | Ratio |
|---|---|---|---|
| Muted / secondary text | `--color-muted` | `#6b5e57` | ~5.3 : 1 |
| Deep rust link (hover) | `--color-rust-deep` | `#9e3b2e` | 6.05 : 1 |
| Near-black (body default) | `--color-fg` | `#2e2b29` | ~14.5 : 1 |

### Automated check

Run `scripts/check-accent-contrast.py` to scan all HTML pages for inline `style` attributes
or utility classes that apply accent color to body-text contexts. The script exits 0 and
reports findings as advisories — it does not block the build. Wire it into code review
sessions, not CI, to avoid false positives from legitimate large-text uses.

```bash
python3 scripts/check-accent-contrast.py
```

---

## Dark Mode Token Reference

Added in Task #26. The Glee-fully dark palette is a warm-dark system — espresso browns replace
the light paper surfaces while coral and gold stay vivid. It activates automatically via
`@media (prefers-color-scheme: dark)` on `.glee-main` pages, and is also triggered explicitly
when `html[data-color-scheme="dark"]` is set by the three-state theme toggle in `app.js`.

### Core token overrides

| Token | Light mode | Dark mode | Dark contrast ratio | Role |
|---|---|---|---|---|
| `--color-bg` | `#f6f2ee` | `#1a1210` | — | Page canvas / body background |
| `--color-surface` | `#fdfbf7` | `#241c1a` | — | Cards, search modal, search page form |
| `--color-surface-soft` | `#f6f2ee` | `#2a2320` | — | Nested panels, nav submenu, search header/footer |
| `--color-fg` | `#2e2b29` | `#f0e8e0` | **16.7 : 1** vs `#1a1210` ✓ | Primary body text |
| `--color-muted` | `#6b5e57` | `#b09080` | **5.9 : 1** vs `#1a1210` ✓ | Secondary/caption text |
| `--color-accent` | `#d94f63` | `#f07585` | **4.9 : 1** vs `#241c1a` ✓ | Links, active nav, focus rings |
| `--color-border-subtle` | *(not set)* | `rgba(240,220,210,0.12)` | — | Hairline dividers in dark context |

> **Why the lightened coral?** The light-mode accent `#d94f63` only reaches 3.37:1 on the
> dark surface `#241c1a` — failing WCAG AA for UI components (3:1 minimum). Lightening to
> `#f07585` lifts it to 4.9:1, comfortably passing for both normal text and UI components.

### Component-specific dark values (not token-driven)

These are hardcoded hex values applied directly to component selectors inside the
`@media (prefers-color-scheme: dark)` block. Use these when building components that
need to match the existing dark chrome:

| Component | Property | Value | Notes |
|---|---|---|---|
| `.site-footer` | background | `#120d0b` | Deepest espresso — slightly darker than page bg |
| `.stripe-bg` (alternate sections) | background | `#1f1512` | Warm very-dark section divider |
| `.site-status` (pre-opening note) | background | `#261616` | Warm red-tinted dark |
| `.site-specials--glee` (sparkle banner) | background | `#3d2b00` | Deep amber-brown |
| `.site-specials--glee` | color | `#f9e4a0` | Warm gold text on amber-brown |
| `.glee-hero-card::before` | box-shadow | `0 20px 45px rgba(0,0,0,0.6)` | Deeper shadow in dark |
| `.latest-pill` | background | `rgba(240,117,133,0.2)` | Coral tint with 20% opacity |
| `.latest-pill` | color | `#f093a5` | Slightly lighter coral |
| Primary nav links | color | `#c7bdb1` | Warm gray-pink — below accent weight |
| Active nav link | color | `#f07585` | Coral accent — matches `--color-accent` |
| `.keep-exploring__link:hover` | background | `#342820` | Warm dark hover state |
| `.construction-overlay__card` | background | `#2a2320` | Matches surface-soft |

### What is unchanged in dark mode

These light-mode values carry forward unchanged (no dark override defined):

- **`--color-border`** (`#d7d7d7`) — only `--color-border-subtle` is overridden; avoid using
  `--color-border` directly in new dark-mode components; use `--color-border-subtle` instead
- **`glee-rust`** / **`glee-gold`** — the named palette constants keep their values; they are
  not used as CSS custom properties in most component rules, so they don't affect dark rendering
- **Stripe palette** (`--okh-teal`, `--okh-olive`, etc.) — these are structural brand tokens and
  are not overridden; the retro stripe hero background is not shown on dark-mode pages

### Editorial rules for dark mode components

1. **Use tokens, not hex** when the value is one of the core 7 tokens above — this ensures
   the three-state toggle's explicit `data-color-scheme="dark"` overrides also apply correctly.
2. **Text on `--color-surface`**: use `--color-fg` (`#f0e8e0`) or `--color-muted` (`#b09080`)
   — both pass WCAG AA.
3. **Accent on dark**: `--color-accent` (`#f07585`) passes 4.9:1 on `--color-surface` and
   9.1:1 on `--color-bg` — safe for links, active states, and focus rings at any text size.
4. **Never use light-mode `#d94f63` in dark contexts** — it fails contrast on all dark surfaces.
5. **Shadows**: increase opacity (e.g., `rgba(0,0,0,0.5)` or higher) — dark backgrounds reduce
   visible shadow contrast, so heavier shadows are needed to maintain depth cues.

*Dark mode palette added 2026-05-27 (Task #26). This reference added 2026-05-28.*

---

*Generated from glee-fully.tools theme — 2026-04-11. Color accessibility section added 2026-05-27. Dark mode section added 2026-05-28.*
