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

*Generated from glee-fully.tools theme — 2026-04-11. Color accessibility section added 2026-05-27.*
