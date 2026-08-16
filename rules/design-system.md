---
description: The accessibility and typography bar for anything Anna builds with a UI. Palette and layout live in each project.
---

# Design system

This file holds the part that travels: the bar every interface has to clear. It does not
hold colors.

**The annaknoll.com palette lives in its own repo and stays there.** The green/violet hue
split, the three ramps, the two page layouts, and the role tables are specific to that site,
where hue carries meaning (green = travel craft, violet = technical craft). Copying them into
an unrelated project would make the hue signal noise.

| I need | Read |
| --- | --- |
| The ramps, roles, and contrast table | `annaknoll-site/design/HANDOFF-design-system.md` |
| The tokens themselves | `annaknoll-site/design/tokens.css` — source of truth, generated |
| To change a color | `annaknoll-site/tools/ramps.json` → `gen_tokens.py`, never by hand |
| To check a ratio | `python3 annaknoll-site/tools/ramps.py` prints the full audit |

FareWatch and JobWatch run their own unrelated palettes. That is fine and they are not being
retrofitted. The rules below still apply to them.

## The accessibility contract

**WCAG 2.2 AAA for text (7:1). AA (3:1) for non-text.** This is stricter than the usual 4.5:1
floor. It is a requirement, not an aspiration.

Five rules, each of which exists because something failed it:

**1. Measure contrast against the ground the text actually sits on.** Not the page background.
A travel comp once reported 5.03:1 for muted text measured against the page; the text sat on
a decorative orb where it measured 2.59:1.

**2. No alpha on any decorative field.** Overlapping translucent fields produce composite
colors you cannot enumerate, so no finite table of ratios can be honest about them. Fully
opaque, always.

**3. Text goes on enumerated grounds only.** Each project names the surfaces text is allowed
to sit on. A surface that isn't on the list is not a text ground, however light it looks.

**4. Color is never the only channel.** Links are underlined. A color bar carries a text label
too. Buttons get a darker bottom border. Hierarchy comes from weight, size, position, and
rules; color only reinforces it.
**Test:** render in `filter: grayscale(1)`. If hierarchy or state disappears, it fails.

**5. Verify in a browser, not from the stylesheet.** Chrome does not apply `:focus-visible` on
a programmatic `.focus()`, so reading the CSS will not tell you whether focus rings work.
Press Tab.

## Code-level requirements

- Landmarks: `<header>`, `<nav>`, `<main id="main">`, `<footer>`. Skip link to `#main`.
- Heading order h1 → h2 → h3 → h4. No skipped levels. Exactly one h1 per page.
- `aria-hidden="true"` on decorative fields.
- Focus ring: `3px solid` at `3px` offset.
- Buttons and CTAs ≥ 44×44px. Inline text links are ~20px tall and qualify under SC 2.5.8's
  inline exception. Don't claim "all controls are 44px" — it isn't true and doesn't need to be.
- `@media (prefers-reduced-motion: reduce)` disables transitions and animation.
- Body line-height ≥ 1.5. Measure ≤ ~70 characters. `text-wrap: balance` on headings.
- `lang="en"` on `<html>`.

## Ramps, if a project needs its own

- Generate both ramps on **one shared OKLCH lightness spine** so equivalent steps carry equal
  perceptual weight. Two hand-picked anchors will not match: green `#2E6B3E` sat at L 0.475
  and violet `#7B4FA0` at L 0.512, so violet read weaker at every equivalent step until both
  were moved to L 0.492.
- **Fills use the 700 step, not 600.** White on a 600 is around 6.6:1, which is AA only.
- **The 400 and 500 steps are never text.** They are for focus rings, icons, borders, chart
  fills, and 24px+ bold display. For lighter body text use a darker neutral, never a tinted 500.
- **One neutral ramp, not one per zone.** A neutral tinted toward one zone puts a thumb on that
  side of every page. One ink is what makes multiple zones read as one sheet of paper.
- Never eyeball a step. Regenerate on the spine.
- Assert the contrast pairs at build time and refuse to write the file if one falls below its
  threshold. `gen_tokens.py` does this; keep the check if you port it.

## Typography

- **A display face is display only.** High thick/thin contrast is a real low-vision problem at
  reading size. Instrument Serif on annaknoll.com is display only, and it ships one weight —
  set `font-weight: 400` explicitly and add `font-synthesis: none` or browsers fake a bold on
  every `<h*>`.
- Pair a serif and a sans drawn as companions and a serif paragraph inside a sans column needs
  no size correction. Faustina and Karla are both Jonny Pinhorn, matched x-height.
- **In a Claude Artifact, a Google Fonts `<link>` fails silently to system fonts** — the CSP
  blocks external hosts. Embed each face as a base64 `@font-face` data URI. Verify with
  `document.fonts.check('400 17px Faustina')`; a silent fallback looks fine until you compare
  letterforms.

## Rejected — do not reintroduce

Warm earth tones on cream. Inter or system-ui as the only typeface. Tailwind slate/gray/zinc
neutrals. Blue/indigo/teal accents. Gradient text. Glassmorphism. Soft drop shadows on
rounded-xl cards. A centered `max-w-4xl` column with a 3-up feature grid.

These are the defaults an LLM reaches for. That is why they are listed.

## Generated assets go stale silently

Social cards and OG images bake copy into pixels. A copy change means regenerating them and
copying the result into the published directory. Nothing checks this and it has drifted twice
in one day. **Treat a copy edit as incomplete until the cards are regenerated.**
